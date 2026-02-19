from __future__ import annotations

import json
import re
from html import unescape
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from ....common.dataloader import ChecklistDataLoader
from ....common.utils import format_date_br
from ....constants import PERFIS_COM_GESTAO
from ....db import query_db
from ....modules.checklist.domain.comments import listar_comentarios_implantacao
from ....modules.implantacao.domain.progress import _get_progress
from ....modules.timeline.application.timeline_service import get_timeline_logs
from ..infra.gemini_client import GeminiClientError, generate_text


def _to_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        v = value.replace("Z", "").split("+")[0]
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(v[:19], fmt)
            except ValueError:
                continue
    return None


def _truncate(text: str, max_len: int, *, preserve_newlines: bool = False) -> str:
    if not text:
        return ""
    text = str(text)
    if preserve_newlines:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    else:
        text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def _strip_datetime_tokens(text: str) -> str:
    if not text:
        return ""
    cleaned = unescape(str(text))
    cleaned = re.sub(
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\s*(?:as|\u00e0s)?\s*\d{1,2}:\d{2}(?::\d{2})?\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "", cleaned)
    cleaned = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", cleaned)
    cleaned = re.sub(
        r"\b\d{1,2}\s+de\s+[a-z\u00e7\u00e3\u00f5\u00e1\u00e9\u00ed\u00f3\u00fa]+\s+de\s+\d{4}\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", cleaned)
    cleaned = re.sub(r"\b\d{1,2}h\d{2}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:as|\u00e0s)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"total\s+de\s+comentarios[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"autores?\s+mais\s+ativos?[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"tarefas?\s+com\s+mais\s+coment[aá]rios?[^.]*\.?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdata\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*[-:]\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,;.-")
    return cleaned


def _normalize_section_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _extract_comment_sentences(comments: list[dict[str, Any]], *, max_len: int = 180) -> list[str]:
    sentences: list[str] = []
    seen: set[str] = set()

    for c in comments:
        raw = c.get("texto") or ""
        texto = _strip_datetime_tokens(raw)
        if not texto:
            continue
        # Evita que um unico comentario "engula" o resumo inteiro.
        per_comment_added = 0
        texto = re.sub(r"\s+", " ", texto).strip(" ,;.-")
        for sent in re.split(r"(?<=[.!?])\s+", texto):
            s = sent.strip(" ,;.-")
            if len(s) < 18:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            s = s[0].upper() + s[1:] if s else s
            sentences.append(_truncate(s, max_len))
            per_comment_added += 1
            if per_comment_added >= 1:
                break
    return sentences


def _pick_thematic_sentences(
    sentences: list[str],
    keywords: tuple[str, ...],
    *,
    limit: int = 8,
) -> list[str]:
    picked: list[str] = []
    for s in sentences:
        lower = s.lower()
        if any(k in lower for k in keywords):
            picked.append(s)
        if len(picked) >= limit:
            break
    return picked


def _join_paragraph(sentences: list[str]) -> str:
    if not sentences:
        return ""
    text = ". ".join(s.rstrip(".") for s in sentences).strip(" .")
    if text and not text.endswith("."):
        text += "."
    return text


def _comment_sort_key(comment: dict[str, Any]) -> datetime:
    dt = _to_datetime(comment.get("data_criacao"))
    return dt or datetime.min


def _build_comments_overview(comments: list[dict[str, Any]], *, company_name: str | None = None) -> str:
    if not comments:
        return "Resumo descritivo: nao ha comentarios registrados nas tarefas ate o momento."

    all_sentences = _extract_comment_sentences(comments, max_len=180)
    if not all_sentences:
        return "Resumo descritivo: nao ha comentarios com conteudo relevante para resumir."

    finance_keywords = (
        "pagamento",
        "parcela",
        "inadimpl",
        "tolerancia zero",
        "bloqueio",
        "carencia",
        "renovacao",
        "matricula",
        "pro-rata",
        "prorrata",
        "cobranca",
        "plano",
    )
    commercial_keywords = (
        "venda",
        "comercial",
        "contrato",
        "modalidade",
        "cpf",
        "telefone",
        "e-mail",
        "email",
        "pin",
        "pix",
        "dinheiro",
        "negociacao",
        "afastamento",
        "ferias",
        "atestado",
        "horario",
        "administrativ",
    )
    access_keywords = (
        "acesso",
        "check-in",
        "checkin",
        "aplicativo",
        "catraca",
        "bike",
        "indoor",
        "credito",
        "trava",
        "minutos",
        "24 horas",
        "antecedencia",
        "integracao",
        "instalacao",
    )

    finance_sentences = _pick_thematic_sentences(all_sentences, finance_keywords, limit=4)
    commercial_sentences = _pick_thematic_sentences(all_sentences, commercial_keywords, limit=4)
    access_sentences = _pick_thematic_sentences(all_sentences, access_keywords, limit=4)

    used = {s.lower() for s in [*finance_sentences, *commercial_sentences, *access_sentences]}
    generic_sentences = [s for s in all_sentences if s.lower() not in used][:3]

    title_suffix = f" - {company_name}" if company_name else ""
    intro = _join_paragraph(generic_sentences) or _join_paragraph(all_sentences[:2])

    blocks = [f"Resumo Descritivo: Treinamento Operacional{title_suffix}", intro]

    if finance_sentences:
        blocks.append("Regras de Negocio e Financeiro")
        blocks.append(_join_paragraph(finance_sentences))
    if commercial_sentences:
        blocks.append("Fluxo Comercial e Administrativo")
        blocks.append(_join_paragraph(commercial_sentences))
    if access_sentences:
        blocks.append("Controle de Acesso e Operacao")
        blocks.append(_join_paragraph(access_sentences))

    result = "\n\n".join([b for b in blocks if b]).strip()
    return _truncate(result, 2400, preserve_newlines=True)

def _enforce_comments_section(structured: dict[str, Any], context: dict[str, Any], source: str) -> dict[str, Any]:
    if not isinstance(structured, dict):
        structured = {}

    sections = structured.get("sections")
    if not isinstance(sections, list):
        sections = []

    company_name = (context.get("implantacao") or {}).get("nome_empresa")
    comments_overview = _build_comments_overview(context.get("comentarios_tarefas", []), company_name=company_name)
    found = False

    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = _normalize_section_title(sec.get("title") or "")
        if "comentarios" not in title:
            continue
        text = str(sec.get("text") or "").strip()
        bullets = [str(b or "").strip() for b in (sec.get("bullets") or []) if str(b or "").strip()]

        # Prioriza o texto original do LLM; usa fallback apenas se vier vazio/ruim.
        if source == "gemini":
            merged_parts = []
            if text:
                merged_parts.append(_strip_datetime_tokens(text))
            if bullets:
                merged_parts.extend([_strip_datetime_tokens(b) for b in bullets])
            merged = "\n\n".join([p for p in merged_parts if p]).strip()
            unique_items = sorted(
                {
                    str(c.get("item_title") or "").strip()
                    for c in context.get("comentarios_tarefas", [])
                    if str(c.get("item_title") or "").strip()
                }
            )
            merged_lower = merged.lower()
            covered_items = [item for item in unique_items if item.lower() in merged_lower]
            min_item_coverage = min(3, len(unique_items))
            has_coverage = len(covered_items) >= min_item_coverage if min_item_coverage > 0 else True
            sec["text"] = merged if (len(merged) >= 120 and has_coverage) else comments_overview
        else:
            sec["text"] = comments_overview
        sec["bullets"] = []
        sec["title"] = "Comentarios e treinamentos"
        found = True
        break

    if not found:
        sections.append(
            {
                "title": "Comentarios e treinamentos",
                "text": comments_overview,
                "bullets": [],
            }
        )

    structured["sections"] = sections
    return structured

def _load_comments_for_summary(impl_id: int, *, per_page: int = 100, max_pages: int = 50) -> dict[str, Any]:
    """
    Carrega comentarios paginados para evitar resumo raso quando ha muito historico.
    Limita paginas para manter latencia previsivel.
    """
    page = 1
    all_comments: list[dict[str, Any]] = []
    total = 0

    while page <= max_pages:
        data = listar_comentarios_implantacao(impl_id, page=page, per_page=per_page)
        batch = data.get("comments", []) or []
        total = int(data.get("total", total) or total)
        if not batch:
            break
        all_comments.extend(batch)
        if len(all_comments) >= total:
            break
        page += 1

    return {"comments": all_comments, "total": total or len(all_comments)}


def _build_context(impl_id: int, user_email: str | None, is_manager: bool) -> dict[str, Any]:
    impl = query_db(
        """
        SELECT
            id, nome_empresa, status, tipo, usuario_cs,
            data_criacao, data_inicio_efetivo, data_previsao_termino,
            data_finalizacao, data_parada, data_cancelamento,
            motivo_parada, motivo_cancelamento
        FROM implantacoes
        WHERE id = %s
        """,
        (impl_id,),
        one=True,
    )
    if not impl:
        raise ValueError("Implantacao nao encontrada.")

    loader = ChecklistDataLoader(impl_id)
    items = loader.get_all_items()
    progress_pct, total_items, completed_items = _get_progress(impl_id)
    leaf_types = {"tarefa", "subtarefa"}

    pending_items: list[dict[str, Any]] = []
    overdue_items: list[dict[str, Any]] = []
    upcoming_items: list[dict[str, Any]] = []

    now = datetime.now()
    upcoming_limit = now + timedelta(days=7)
    for item in items:
        if item.get("tipo_item") not in leaf_types:
            continue
        completed = bool(item.get("completed"))
        prazo_fim = _to_datetime(item.get("prazo_fim"))
        if not completed:
            pending_items.append(
                {
                    "id": item.get("id"),
                    "titulo": _truncate(item.get("title") or "", 120),
                    "responsavel": item.get("responsavel"),
                    "prazo_fim": format_date_br(prazo_fim) if prazo_fim else None,
                }
            )
            if prazo_fim and prazo_fim.date() < now.date():
                overdue_items.append(pending_items[-1])
            elif prazo_fim and now.date() <= prazo_fim.date() <= upcoming_limit.date():
                upcoming_items.append(pending_items[-1])

    comments_data = _load_comments_for_summary(impl_id, per_page=100, max_pages=50)
    comments = comments_data.get("comments", [])
    comments = sorted(comments, key=_comment_sort_key, reverse=True)
    comments_total = comments_data.get("total", len(comments))
    comments_for_summary = [
        {
            "id": c.get("id"),
            "autor": c.get("usuario_nome") or c.get("usuario_cs"),
            "item_title": _truncate(c.get("item_title") or "Tarefa", 90),
            "texto": c.get("texto") or "",
        }
        for c in comments
        if (c.get("texto") or "").strip()
    ]
    recent_comments = [
        {
            "id": c.get("id"),
            "autor": c.get("usuario_nome") or c.get("usuario_cs"),
            "texto": _truncate(c.get("texto") or "", 240),
            "tag": c.get("tag"),
            "data": c.get("data_criacao"),
            "imagem_url": c.get("imagem_url"),
            "item_title": c.get("item_title"),
        }
        for c in comments
    ]

    meeting_comments = [
        c
        for c in recent_comments
        if (c.get("tag") and "reun" in c.get("tag", "").lower())
        or ("reun" in (c.get("texto") or "").lower())
    ]

    attachments = [c for c in recent_comments if c.get("imagem_url")]

    # Estatisticas de comentarios
    tag_counts = Counter([c.get("tag") for c in recent_comments if c.get("tag")])
    top_tags = [f"{tag} ({count})" for tag, count in tag_counts.most_common(6)]
    author_counts = Counter([c.get("autor") for c in recent_comments if c.get("autor")])
    top_authors = [f"{author} ({count})" for author, count in author_counts.most_common(5)]
    task_counts = Counter([c.get("item_title") for c in recent_comments if c.get("item_title")])
    top_tasks = [f"{task} ({count})" for task, count in task_counts.most_common(5)]

    treinamentos = []
    for c in recent_comments:
        text = (c.get("texto") or "").lower()
        tag = (c.get("tag") or "").lower()
        if any(k in text for k in ["trein", "capacita", "onboard", "aula", "workshop"]) or any(
            k in tag for k in ["trein", "reun", "kickoff", "welcome"]
        ):
            snippet = _truncate(c.get("texto") or "", 140)
            tarefa = c.get("item_title") or "Tarefa"
            treinamentos.append(f"{tarefa}: {snippet}")
        if len(treinamentos) >= 8:
            break

    comentarios_highlights = []
    for c in recent_comments[:12]:
        titulo = c.get("item_title") or "Tarefa"
        comentarios_highlights.append(
            f"{titulo} - {c.get('autor') or 'N/A'}: {c.get('texto')}"
        )

    timeline = get_timeline_logs(impl_id=impl_id, page=1, per_page=30)
    timeline_logs = timeline.get("logs", [])

    last_activity = query_db(
        "SELECT MAX(data_criacao) as last_activity FROM timeline_log WHERE implantacao_id = %s",
        (impl_id,),
        one=True,
    )
    last_activity_dt = _to_datetime(last_activity.get("last_activity") if last_activity else None)

    riscos: list[str] = []
    if impl.get("status") == "parada":
        riscos.append("Implantacao esta parada.")
    if impl.get("status") == "cancelada":
        riscos.append("Implantacao foi cancelada.")
    if overdue_items:
        riscos.append(f"{len(overdue_items)} tarefa(s) com prazo estourado.")
    previsao = _to_datetime(impl.get("data_previsao_termino"))
    if previsao and previsao.date() < now.date() and impl.get("status") not in {"finalizada", "cancelada"}:
        riscos.append("Prazo previsto ultrapassado.")
    if last_activity_dt and (now - last_activity_dt).days >= 14:
        riscos.append("Sem movimentacao na timeline ha 14+ dias.")

    return {
        "implantacao": {
            "id": impl.get("id"),
            "nome_empresa": impl.get("nome_empresa"),
            "status": impl.get("status"),
            "tipo": impl.get("tipo"),
            "usuario_cs": impl.get("usuario_cs"),
            "data_criacao": format_date_br(impl.get("data_criacao")),
            "data_inicio_efetivo": format_date_br(impl.get("data_inicio_efetivo")),
            "data_previsao_termino": format_date_br(impl.get("data_previsao_termino")),
            "data_finalizacao": format_date_br(impl.get("data_finalizacao")),
            "data_parada": format_date_br(impl.get("data_parada")),
            "data_cancelamento": format_date_br(impl.get("data_cancelamento")),
            "motivo_parada": _truncate(impl.get("motivo_parada") or "", 180),
            "motivo_cancelamento": _truncate(impl.get("motivo_cancelamento") or "", 180),
        },
        "progresso": {
            "percentual": progress_pct,
            "total_itens": total_items,
            "concluidos": completed_items,
        },
        "pendencias": {
            "total": len(pending_items),
            "overdue_total": len(overdue_items),
            "upcoming_total": len(upcoming_items),
            "overdue_itens": overdue_items[:10],
            "upcoming_itens": upcoming_items[:10],
        },
        "timeline": timeline_logs[:20],
        "comentarios_recentes": recent_comments[:25],
        "comentarios_tarefas": comments_for_summary,
        "comentarios_reunioes": meeting_comments[:15],
        "anexos_recentes": attachments[:10],
        "comentarios_total": comments_total,
        "tags_top": top_tags,
        "autores_top": top_authors,
        "tarefas_top": top_tasks,
        "treinamentos": treinamentos,
        "comentarios_highlights": comentarios_highlights,
        "riscos": riscos,
        "metadados": {
            "gerado_por": user_email,
            "is_manager": is_manager,
        },
    }


def _build_minimal_context(impl_id: int, user_email: str | None, is_manager: bool) -> dict[str, Any]:
    impl = query_db(
        """
        SELECT id, nome_empresa, status, tipo, usuario_cs, data_criacao
        FROM implantacoes
        WHERE id = %s
        """,
        (impl_id,),
        one=True,
    )
    if not impl:
        raise ValueError("Implantacao nao encontrada.")

    try:
        progress_pct, total_items, completed_items = _get_progress(impl_id)
    except Exception:
        progress_pct, total_items, completed_items = 0, 0, 0

    return {
        "implantacao": {
            "id": impl.get("id"),
            "nome_empresa": impl.get("nome_empresa"),
            "status": impl.get("status"),
            "tipo": impl.get("tipo"),
            "usuario_cs": impl.get("usuario_cs"),
            "data_criacao": format_date_br(impl.get("data_criacao")),
            "data_inicio_efetivo": "Nao informado",
            "data_previsao_termino": "Nao informado",
            "data_finalizacao": "Nao informado",
            "data_parada": "Nao informado",
            "data_cancelamento": "Nao informado",
            "motivo_parada": "",
            "motivo_cancelamento": "",
        },
        "progresso": {
            "percentual": progress_pct,
            "total_itens": total_items,
            "concluidos": completed_items,
        },
        "pendencias": {
            "total": 0,
            "overdue_total": 0,
            "upcoming_total": 0,
            "overdue_itens": [],
            "upcoming_itens": [],
        },
        "timeline": [],
        "comentarios_recentes": [],
        "comentarios_tarefas": [],
        "comentarios_reunioes": [],
        "anexos_recentes": [],
        "comentarios_total": 0,
        "tags_top": [],
        "autores_top": [],
        "tarefas_top": [],
        "treinamentos": [],
        "comentarios_highlights": [],
        "riscos": [],
        "metadados": {
            "gerado_por": user_email,
            "is_manager": is_manager,
        },
    }


def _build_prompt(context: dict[str, Any]) -> str:
    return (
        "Voce e um assistente que gera relatorios completos para CS Onboarding.\n"
        "Responda APENAS em JSON valido, sem texto extra.\n"
        "Use as chaves exatamente como abaixo. Se algo nao existir, use 'Nao informado' ou lista vazia.\n\n"
        "Chaves obrigatorias:\n"
        "- header: {title, subtitle, empresa, status, metrics[]}\n"
        "- sections: lista de objetos com {title, text, bullets}\n\n"
        "Secoes (na ordem):\n"
        "1. Resumo executivo\n"
        "2. Andamento atual\n"
        "3. Pendencias e prazos\n"
        "4. Comentarios e treinamentos\n"
        "5. Tags e temas recorrentes\n"
        "6. Anexos e evidencias\n"
        "7. Ultimos eventos relevantes\n"
        "8. Proximos passos sugeridos\n\n"
        "Regra obrigatoria para 'Comentarios e treinamentos':\n"
        "- Gere texto descritivo com subtitulos tematicos exatamente nesta ordem quando houver conteudo:\n"
        "  1) Regras de Negocio e Financeiro\n"
        "  2) Fluxo Comercial e Administrativo\n"
        "  3) Controle de Acesso e Operacao\n"
        "- Use TODOS os comentarios das tarefas fornecidos no contexto.\n"
        "- Quando houver varios comentarios, cubra multiplas frentes e nao foque em um unico comentario.\n"
        "- Nao exiba total de comentarios, contagens, data ou horario.\n\n"
        "Dados estruturados (JSON):\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )


def _structured_fallback(context: dict[str, Any]) -> dict[str, Any]:
    imp = context.get("implantacao", {})
    prog = context.get("progresso", {})
    pend = context.get("pendencias", {})
    riscos = context.get("riscos", [])
    timeline = context.get("timeline", [])
    tags_top = context.get("tags_top", [])
    comentarios_tarefas = context.get("comentarios_tarefas", [])
    comentarios_total = context.get("comentarios_total", 0)
    anexos = context.get("anexos_recentes", [])

    sections = [
        {
            "title": "Resumo executivo",
            "text": (
                f"Implantacao de {imp.get('nome_empresa', 'N/A')} em status {imp.get('status', 'N/A')}."
            ),
            "bullets": [],
        },
        {
            "title": "Andamento atual",
            "text": (
                f"{prog.get('percentual', 0)}% ({prog.get('concluidos', 0)}/{prog.get('total_itens', 0)} itens)."
            ),
            "bullets": [],
        },
        {
            "title": "Pendencias e prazos",
            "text": (
                f"{pend.get('total', 0)} abertas, {pend.get('overdue_total', 0)} atrasadas, "
                f"{pend.get('upcoming_total', 0)} nos proximos 7 dias."
            ),
            "bullets": [
                *[
                    f"Atraso: {i.get('titulo')} (prazo {i.get('prazo_fim')})"
                    for i in pend.get("overdue_itens", [])[:5]
                ],
                *[
                    f"Proximo: {i.get('titulo')} (prazo {i.get('prazo_fim')})"
                    for i in pend.get("upcoming_itens", [])[:5]
                ],
            ],
        },
        {
            "title": "Comentarios e treinamentos",
            "text": _build_comments_overview(comentarios_tarefas),
            "bullets": [],
        },
        {
            "title": "Tags e temas recorrentes",
            "text": "Principais tags identificadas.",
            "bullets": tags_top[:8] if tags_top else ["Nao informado."],
        },
        {
            "title": "Anexos e evidencias",
            "text": f"{len(anexos)} anexo(s) recente(s).",
            "bullets": [f"{a.get('data')}: {a.get('imagem_url')}" for a in anexos[:6]] or ["Nao informado."],
        },
        {
            "title": "Ultimos eventos relevantes",
            "text": "",
            "bullets": [
                f"{t.get('data_criacao')}: {t.get('tipo_evento')} - {t.get('detalhes')}"
                for t in timeline[:6]
            ]
            or ["Nao informado."],
        },
        {
            "title": "Proximos passos sugeridos",
            "text": "",
            "bullets": [
                "Revisar pendencias e validar prazos com o cliente.",
                "Garantir registro de treinamentos e alinhamentos recentes.",
            ],
        },
    ]

    return {
        "header": {
            "title": "Resumo da Implantacao",
            "subtitle": "Documento sintetico do andamento",
            "empresa": imp.get("nome_empresa", "N/A"),
            "status": imp.get("status", "N/A"),
            "metrics": [
                {"label": "Progresso", "value": f"{prog.get('percentual', 0)}%"},
                {"label": "Itens", "value": f"{prog.get('concluidos', 0)}/{prog.get('total_itens', 0)}"},
                {"label": "Comentarios", "value": str(comentarios_total)},
                {"label": "Tags", "value": str(len(tags_top))},
            ],
        },
        "sections": sections,
    }


def _structured_to_text(structured: dict[str, Any]) -> str:
    sections = structured.get("sections", [])
    mapping = {
        "Resumo executivo": "Resumo executivo",
        "Andamento atual": "Andamento",
        "Pendencias e prazos": "Pendencias",
        "Comentarios e treinamentos": "Comentarios e treinamentos",
        "Tags e temas recorrentes": "Tags e temas",
        "Anexos e evidencias": "Anexos",
        "Ultimos eventos relevantes": "Ultimos eventos",
        "Proximos passos sugeridos": "Proximos passos sugeridos",
    }
    lines = []
    for sec in sections:
        title = mapping.get(sec.get("title"), sec.get("title", "Secao"))
        text = (sec.get("text") or "").strip()
        bullets = sec.get("bullets") or []
        line = f"{title}: {text}" if text else f"{title}:"
        if bullets:
            line += " " + "; ".join([str(b) for b in bullets[:4]])
        lines.append(line)
    return "\n".join(lines)


def gerar_resumo_implantacao_service(
    impl_id: int,
    user_email: str | None = None,
    perfil_acesso: str | None = None,
) -> dict[str, Any]:
    is_manager = bool(perfil_acesso in PERFIS_COM_GESTAO) if perfil_acesso else False
    try:
        context = _build_context(impl_id, user_email, is_manager)
    except Exception:
        context = _build_minimal_context(impl_id, user_email, is_manager)
    prompt = _build_prompt(context)

    summary_structured: dict[str, Any] | None = None
    try:
        summary_text = generate_text(prompt)
        source = "gemini"
        # Tentar extrair JSON
        raw = summary_text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(json)?", "", raw.strip(), flags=re.IGNORECASE).strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        if raw.startswith("{") and raw.endswith("}"):
            try:
                summary_structured = json.loads(raw)
            except Exception:
                summary_structured = None
        if summary_structured is None:
            summary_structured = _structured_fallback(context)
            source = "fallback"
    except GeminiClientError:
        summary_structured = _structured_fallback(context)
        source = "fallback"
    except Exception:
        summary_structured = _structured_fallback(context)
        source = "fallback"

    summary_structured = _enforce_comments_section(summary_structured, context, source)
    summary_text = _structured_to_text(summary_structured)

    return {
        "summary": summary_text,
        "summary_structured": summary_structured,
        "source": source,
    }

