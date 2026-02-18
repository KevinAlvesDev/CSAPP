from __future__ import annotations

import json
import re
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


def _truncate(text: str, max_len: int) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


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

    comments_data = listar_comentarios_implantacao(impl_id, page=1, per_page=120)
    comments = comments_data.get("comments", [])
    comments_total = comments_data.get("total", len(comments))
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
        if any(k in text for k in ["trein", "capacita", "onboard", "aula", "workshop"]):
            snippet = _truncate(c.get("texto") or "", 140)
            treinamentos.append(f"{c.get('data')}: {snippet}")
        if len(treinamentos) >= 8:
            break

    comentarios_highlights = []
    for c in recent_comments[:12]:
        titulo = c.get("item_title") or "Tarefa"
        comentarios_highlights.append(
            f"{c.get('data')}: {titulo} - {c.get('autor') or 'N/A'}: {c.get('texto')}"
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


def _build_prompt(context: dict[str, Any]) -> str:
    return (
        "Voce e um assistente que gera relatorios completos para CS Onboarding.\n"
        "Responda APENAS em JSON valido, sem texto extra.\n"
        "Use as chaves exatamente como abaixo. Se algo nao existir, use 'Nao informado' ou lista vazia.\n\n"
        "Chaves obrigatorias:\n"
        "- header: {title, subtitle, empresa, status}\n"
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
    autores_top = context.get("autores_top", [])
    tarefas_top = context.get("tarefas_top", [])
    treinamentos = context.get("treinamentos", [])
    comentarios_total = context.get("comentarios_total", 0)
    comentarios_highlights = context.get("comentarios_highlights", [])
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
            "text": (
                f"Total de comentarios: {comentarios_total}. "
                f"Autores mais ativos: {', '.join(autores_top) if autores_top else 'Nao informado.'} "
                f"Tarefas com mais comentarios: {', '.join(tarefas_top) if tarefas_top else 'Nao informado.'}"
            ),
            "bullets": [
                *treinamentos[:6],
                *comentarios_highlights[:6],
            ],
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
    context = _build_context(impl_id, user_email, is_manager)
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
    except GeminiClientError:
        summary_structured = _structured_fallback(context)
        summary_text = _structured_to_text(summary_structured)
        source = "fallback"

    return {
        "summary": summary_text,
        "summary_structured": summary_structured,
        "source": source,
    }
