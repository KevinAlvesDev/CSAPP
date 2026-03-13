from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from html import unescape
from typing import Any

from ....common.dataloader import ChecklistDataLoader
from ....common.utils import format_date_br
from ....constants import PERFIS_COM_GESTAO
from ....db import query_db
from ....modules.checklist.domain.comments import listar_comentarios_implantacao
from ....modules.implantacao.domain.progress import _get_progress
from ....modules.timeline.application.timeline_service import get_timeline_logs
from ..infra.gemini_client import GeminiClientError, generate_text


def _strip_html(text: str) -> str:
    """Remove tags HTML e entidades de um texto."""
    if not text:
        return ""
    cleaned = unescape(str(text))
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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
    """Garante que a secao de comentarios tenha conteudo de qualidade."""
    if not isinstance(structured, dict):
        structured = {}

    sections = structured.get("sections")
    if not isinstance(sections, list):
        sections = []

    company_name = (context.get("implantacao") or {}).get("nome_empresa")
    comments_overview = _build_comments_overview(context.get("comentarios_tarefas", []), company_name=company_name)

    for sec in sections:
        if not isinstance(sec, dict):
            continue
        title = _normalize_section_title(sec.get("title") or "")
        if "comentarios" not in title and "reuniao" not in title and "reunioes" not in title:
            continue
        text = str(sec.get("text") or "").strip()
        if source == "gemini" and len(text) >= 120:
            sec["text"] = _strip_datetime_tokens(text)
        else:
            sec["text"] = comments_overview
        sec["bullets"] = []
        sec["title"] = "Comentarios e Reunioes"
        break

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

    # Nome do CS responsavel (tabela usuario e do OAMD, pode nao existir)
    cs_nome: str | None = None
    cs_email = impl.get("usuario_cs")
    if cs_email:
        try:
            cs_row = query_db("SELECT nome FROM usuario WHERE email = %s", (cs_email,), one=True)
            if cs_row and cs_row.get("nome"):
                cs_nome = cs_row.get("nome")
        except Exception:
            pass
    cs_nome = cs_nome or cs_email or "N/A"

    loader = ChecklistDataLoader(impl_id)
    items = loader.get_all_items()
    progress_pct, total_items, completed_items = _get_progress(impl_id)
    leaf_types = {"tarefa", "subtarefa"}

    now = datetime.now(timezone.utc)
    upcoming_limit = now + timedelta(days=7)

    # Dias em andamento
    start_dt = _to_datetime(impl.get("data_inicio_efetivo"))
    dias_em_andamento: int | None = (now.date() - start_dt.date()).days if start_dt else None

    # Grupos/fases do checklist com progresso
    root_items = [i for i in items if not i.get("parent_id")]
    checklist_grupos: list[dict[str, Any]] = []
    for grupo in root_items[:20]:
        gid = grupo.get("id")
        filhos_folha = [
            i for i in items
            if i.get("tipo_item") in leaf_types and _is_descendant(items, i, gid)
        ]
        total_g = len(filhos_folha)
        done_g = sum(1 for i in filhos_folha if i.get("completed"))
        pct_g = int(done_g / total_g * 100) if total_g else 0
        checklist_grupos.append({
            "titulo": _truncate(grupo.get("title") or "", 80),
            "total": total_g,
            "concluidos": done_g,
            "percentual": pct_g,
        })

    pending_items: list[dict[str, Any]] = []
    overdue_items: list[dict[str, Any]] = []
    upcoming_items: list[dict[str, Any]] = []

    for item in items:
        if item.get("tipo_item") not in leaf_types:
            continue
        if bool(item.get("completed")):
            continue
        prazo_fim = _to_datetime(item.get("prazo_fim"))
        entry = {
            "titulo": _truncate(item.get("title") or "", 100),
            "responsavel": item.get("responsavel") or "N/A",
            "prazo_fim": format_date_br(prazo_fim) if prazo_fim else None,
        }
        pending_items.append(entry)
        if prazo_fim and prazo_fim.date() < now.date():
            dias_atraso = (now.date() - prazo_fim.date()).days
            overdue_items.append({**entry, "dias_atraso": dias_atraso})
        elif prazo_fim and now.date() <= prazo_fim.date() <= upcoming_limit.date():
            upcoming_items.append(entry)

    comments_data = _load_comments_for_summary(impl_id, per_page=100, max_pages=50)
    all_comments = comments_data.get("comments", [])
    comments_total = comments_data.get("total", len(all_comments))

    # Cronologico: mais antigo primeiro (para narrativa)
    comments_chrono = sorted(all_comments, key=_comment_sort_key)
    # Mais recente primeiro (para highlights rapidos)
    comments_recent = sorted(all_comments, key=_comment_sort_key, reverse=True)

    comments_for_summary = [
        {
            "autor": c.get("usuario_nome") or c.get("usuario_cs"),
            "item_title": _truncate(c.get("item_title") or "Tarefa", 80),
            "texto": _truncate(c.get("texto") or "", 300),
            "tag": c.get("tag"),
        }
        for c in comments_chrono
        if (c.get("texto") or "").strip()
    ]

    attachments = [
        {
            "autor": c.get("usuario_nome") or c.get("usuario_cs"),
            "item_title": c.get("item_title"),
            "imagem_url": c.get("imagem_url"),
        }
        for c in comments_recent
        if c.get("imagem_url")
    ]

    tag_counts = Counter([c.get("tag") for c in all_comments if c.get("tag")])
    top_tags = [tag for tag, _ in tag_counts.most_common(6)]
    author_counts = Counter(
        [c.get("usuario_nome") or c.get("usuario_cs") for c in all_comments
         if c.get("usuario_nome") or c.get("usuario_cs")]
    )
    top_authors = [f"{a} ({n}x)" for a, n in author_counts.most_common(5)]

    # Timeline: get_timeline_logs retorna data_criacao ja formatada e em ordem DESC
    timeline = get_timeline_logs(impl_id=impl_id, page=1, per_page=50)
    timeline_logs_raw = timeline.get("logs", [])
    # Reverter para cronologico (mais antigo primeiro)
    timeline_entries = [
        {
            "data": t.get("data_criacao") or "N/A",
            "tipo": t.get("tipo_evento") or "",
            "detalhe": _truncate(_strip_html(str(t.get("detalhes") or "")), 120),
        }
        for t in reversed(timeline_logs_raw[:50])
    ]

    # data da ultima atividade (primeiro item = mais recente)
    last_activity_dt = _to_datetime(
        timeline_logs_raw[0].get("data_criacao") if timeline_logs_raw else None
    )
    # Se _to_datetime falhou (string BR), estimar pela posicao (log mais recente existe = ativo recentemente)
    if last_activity_dt is None and timeline_logs_raw:
        last_activity_dt = datetime.now(timezone.utc)  # assume ativo, sem alerta de inatividade

    riscos: list[str] = []
    if impl.get("status") == "parada":
        motivo = impl.get("motivo_parada") or ""
        riscos.append(f"Implantacao esta parada. Motivo: {motivo}" if motivo else "Implantacao esta parada.")
    if impl.get("status") == "cancelada":
        riscos.append("Implantacao foi cancelada.")
    if overdue_items:
        riscos.append(f"{len(overdue_items)} tarefa(s) com prazo vencido.")
    previsao = _to_datetime(impl.get("data_previsao_termino"))
    if previsao and previsao.date() < now.date() and impl.get("status") not in {"finalizada", "cancelada"}:
        riscos.append("Previsao de termino ja ultrapassada.")
    if last_activity_dt:
        dias_inativo = (now - last_activity_dt).days if last_activity_dt.tzinfo else (datetime.utcnow() - last_activity_dt).days
        if dias_inativo >= 14:
            riscos.append(f"Sem movimentacao registrada ha {dias_inativo} dias.")

    return {
        "implantacao": {
            "id": impl.get("id"),
            "nome_empresa": impl.get("nome_empresa"),
            "status": impl.get("status"),
            "tipo": impl.get("tipo"),
            "cs_responsavel": cs_nome,
            "data_criacao": format_date_br(impl.get("data_criacao")),
            "data_inicio_efetivo": format_date_br(impl.get("data_inicio_efetivo")) or "Nao iniciada",
            "data_previsao_termino": format_date_br(impl.get("data_previsao_termino")) or "Sem previsao",
            "data_finalizacao": format_date_br(impl.get("data_finalizacao")),
            "data_parada": format_date_br(impl.get("data_parada")),
            "data_cancelamento": format_date_br(impl.get("data_cancelamento")),
            "motivo_parada": _truncate(impl.get("motivo_parada") or "", 200),
            "motivo_cancelamento": _truncate(impl.get("motivo_cancelamento") or "", 200),
            "dias_em_andamento": dias_em_andamento,
        },
        "progresso": {
            "percentual": progress_pct,
            "total_itens": total_items,
            "concluidos": completed_items,
            "pendentes": total_items - completed_items,
        },
        "checklist_grupos": checklist_grupos,
        "pendencias": {
            "total_abertas": len(pending_items),
            "overdue_total": len(overdue_items),
            "upcoming_total": len(upcoming_items),
            "overdue_itens": overdue_items[:8],
            "upcoming_itens": upcoming_items[:8],
        },
        "timeline": timeline_entries,
        "comentarios_tarefas": comments_for_summary[:30],
        "anexos_recentes": attachments[:8],
        "comentarios_total": comments_total,
        "tags_frequentes": top_tags,
        "autores_ativos": top_authors,
        "riscos": riscos,
        "metadados": {
            "gerado_por": user_email,
            "is_manager": is_manager,
        },
    }


def _is_descendant(items: list[dict[str, Any]], item: dict[str, Any], ancestor_id: Any) -> bool:
    """Verifica se um item descende de ancestor_id na arvore do checklist."""
    parent = item.get("parent_id")
    visited: set = set()
    while parent is not None:
        if parent in visited:
            break
        visited.add(parent)
        if parent == ancestor_id:
            return True
        parent_item = next((i for i in items if i.get("id") == parent), None)
        parent = parent_item.get("parent_id") if parent_item else None
    return False


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
    except Exception as exc:
        logger.exception("Unhandled exception", exc_info=True)
        progress_pct, total_items, completed_items = 0, 0, 0

    return {
        "implantacao": {
            "id": impl.get("id"),
            "nome_empresa": impl.get("nome_empresa"),
            "status": impl.get("status"),
            "tipo": impl.get("tipo"),
            "cs_responsavel": impl.get("usuario_cs") or "N/A",
            "data_criacao": format_date_br(impl.get("data_criacao")),
            "data_inicio_efetivo": "Nao informado",
            "data_previsao_termino": "Nao informado",
            "data_finalizacao": "Nao informado",
            "data_parada": "Nao informado",
            "data_cancelamento": "Nao informado",
            "motivo_parada": "",
            "motivo_cancelamento": "",
            "dias_em_andamento": None,
        },
        "progresso": {
            "percentual": progress_pct,
            "total_itens": total_items,
            "concluidos": completed_items,
            "pendentes": total_items - completed_items,
        },
        "checklist_grupos": [],
        "pendencias": {
            "total_abertas": 0,
            "overdue_total": 0,
            "upcoming_total": 0,
            "overdue_itens": [],
            "upcoming_itens": [],
        },
        "timeline": [],
        "comentarios_tarefas": [],
        "anexos_recentes": [],
        "comentarios_total": 0,
        "tags_frequentes": [],
        "autores_ativos": [],
        "riscos": [],
        "metadados": {
            "gerado_por": user_email,
            "is_manager": is_manager,
        },
    }


def _build_prompt(context: dict[str, Any]) -> str:
    imp = context.get("implantacao", {})
    prog = context.get("progresso", {})
    pend = context.get("pendencias", {})
    grupos = context.get("checklist_grupos", [])
    timeline = context.get("timeline", [])
    comentarios = context.get("comentarios_tarefas", [])
    riscos = context.get("riscos", [])
    tags = context.get("tags_frequentes", [])
    autores = context.get("autores_ativos", [])

    grupos_txt = "\n".join(
        f"  - {g['titulo']}: {g['concluidos']}/{g['total']} ({g['percentual']}%)"
        for g in grupos
    ) or "  Nao disponivel."

    timeline_txt = "\n".join(
        f"  [{t['data']}] {t['tipo']}: {_strip_html(t['detalhe'])}"
        for t in timeline
        if t.get("tipo") and t.get("detalhe")
    ) or "  Nenhum evento registrado."

    overdue_txt = "\n".join(
        f"  - {i['titulo']} | Responsavel: {i['responsavel']} | Venceu ha {i.get('dias_atraso', '?')} dias"
        for i in pend.get("overdue_itens", [])
    ) or "  Nenhuma tarefa atrasada."

    upcoming_txt = "\n".join(
        f"  - {i['titulo']} | Responsavel: {i['responsavel']} | Prazo: {i['prazo_fim']}"
        for i in pend.get("upcoming_itens", [])
    ) or "  Nenhuma tarefa com prazo proximo."

    riscos_txt = "\n".join(f"  ! {r}" for r in riscos) or "  Nenhum risco critico identificado."

    comentarios_txt = "\n".join(
        f"  [{c['item_title']}] {c['autor']}: {c['texto']}"
        for c in comentarios[:25]
    ) or "  Nenhum comentario registrado."

    dias_label = f"{imp.get('dias_em_andamento')} dias" if imp.get("dias_em_andamento") is not None else "N/A"

    return f"""Voce e um gerente de projetos senior de Customer Success que redige relatorios executivos internos para diretores de operacoes.

Escreva o relatorio abaixo em TEXTO CORRIDO, em portugues, tom direto e profissional — como se estivesse descrevendo a situacao em voz alta para um colega senior. Use linguagem precisa, nao burocratica.

REGRAS OBRIGATORIAS:
- Texto corrido em paragrafos. ZERO listas, ZERO bullets, ZERO hifens como marcador.
- Use **negrito** para destacar nomes de empresa, pessoas, datas criticas e numeros relevantes diretamente no texto — nao apenas nos subtitulos.
- Use subtitulos em negrito em linha propria (ex: **Como chegamos ate aqui**).
- LIMITE RIGOROSO: maximo 450 palavras no total. Cada paragrafo: maximo 4 frases. Seja denso — cada frase deve carregar informacao real, nao repeticoes.
- NAO use JSON. NAO use markdown com # ou -.
- Se o prazo de termino ja passou, mencione isso explicitamente com urgencia.
- Se nao houver riscos criticos, diga isso em uma frase e passe para o proximo ponto.
- PARE assim que terminar os 5 subtitulos. Nao adicione introducao antes do primeiro subtitulo nem conclusao depois do ultimo.

---
DADOS DA IMPLANTACAO:
Empresa: {imp.get('nome_empresa')} | Status: {imp.get('status')} | CS: {imp.get('cs_responsavel')}
Inicio efetivo: {imp.get('data_inicio_efetivo')} | Dias em andamento: {dias_label}
Previsao de termino: {imp.get('data_previsao_termino')} | Finalizado em: {imp.get('data_finalizacao') or 'nao finalizado'}
Parado em: {imp.get('data_parada') or 'nao'} | Motivo parada: {imp.get('motivo_parada') or 'N/A'}
Cancelado em: {imp.get('data_cancelamento') or 'nao'}

PROGRESSO: {prog.get('percentual', 0)}% — {prog.get('concluidos', 0)}/{prog.get('total_itens', 0)} itens | {pend.get('total_abertas', 0)} abertas | {pend.get('overdue_total', 0)} atrasadas | {pend.get('upcoming_total', 0)} vencem em 7 dias

FASES DO CHECKLIST:
{grupos_txt}

TAREFAS ATRASADAS:
{overdue_txt}

TAREFAS VENCENDO EM 7 DIAS:
{upcoming_txt}

ALERTAS:
{riscos_txt}

TIMELINE (cronologica, mais antigo primeiro — use para contar a historia):
{timeline_txt}

COMENTARIOS NAS TAREFAS (cronologicos — use para enriquecer a narrativa):
{comentarios_txt}

AUTORES ATIVOS: {', '.join(autores) if autores else 'N/A'}

---
ESCREVA O RELATORIO COM EXATAMENTE ESTA ESTRUTURA:

**Resumo Executivo**
[1 paragrafo, max 3 frases: empresa em negrito, CS em negrito, status, progresso %, inicio e previsao. Se prazo passou, diga explicitamente.]

**Como chegamos ate aqui**
[1 paragrafo, max 4 frases: cronologia real da timeline — criacao, inicio, paradas, retomadas. Use apenas eventos que existem nos dados, sem inventar.]

**Onde estamos hoje**
[1 paragrafo, max 4 frases: fases concluidas pelo nome, fases em andamento com %, fases nao iniciadas. Mencione o que o cliente aguarda se houver nos comentarios.]

**Pendencias e Riscos**
[1 paragrafo, max 3 frases: tarefas atrasadas pelo nome e ha quantos dias. Prazos proximos. Alertas ativos. Se nao houver, diga em 1 frase.]

**Proximos Passos**
[1 paragrafo, max 3 frases: acoes especificas e concretas. O QUE fazer, COM QUEM e POR QUE. Sem generalizacoes.]"""


def _narrative_fallback(context: dict[str, Any]) -> str:
    """Gera narrativa em texto corrido sem depender do Gemini."""
    imp = context.get("implantacao", {})
    prog = context.get("progresso", {})
    pend = context.get("pendencias", {})
    riscos = context.get("riscos", [])
    timeline = context.get("timeline", [])
    grupos = context.get("checklist_grupos", [])

    empresa = imp.get("nome_empresa", "N/A")
    status = imp.get("status", "N/A")
    cs = imp.get("cs_responsavel", "N/A")
    dias = imp.get("dias_em_andamento")
    dias_label = f"{dias} dias" if dias is not None else "período não informado"
    pct = prog.get("percentual", 0)
    total = prog.get("total_itens", 0)
    concluidos = prog.get("concluidos", 0)
    previsao = imp.get("data_previsao_termino") or "sem previsão definida"
    inicio = imp.get("data_inicio_efetivo") or "não informado"

    # Formata CS: se for e-mail, exibe apenas a parte antes do @
    cs_display = cs.split("@")[0] if "@" in cs else cs

    resumo = (
        f"A implantação de **{empresa}**, conduzida por {cs_display}, encontra-se atualmente com status "
        f"'{status}'. O processo registra {pct}% de conclusão ({concluidos}/{total} itens concluídos), "
        f"com início efetivo em {inicio} e previsão de término em {previsao}."
    )

    # Filtra apenas eventos relevantes para narrativa (ignora ruídos operacionais)
    _NOISE_TYPES = {"novo_comentario", "detalhes_alterados", "prazo_alterado", "responsavel_alterado"}
    _LABEL_MAP = {
        "criacao": "criação da implantação",
        "status_alterado": "alteração de status",
        "parada": "implantação pausada",
        "retomada": "retomada do processo",
        "finalizada": "conclusão da implantação",
        "cancelada": "cancelamento",
        "plano_aplicado": "plano de sucesso aplicado",
        "plano_concluido": "plano de sucesso concluído",
        "inicio": "início efetivo",
    }
    eventos_filtrados = [
        t for t in timeline
        if t.get("tipo") and t.get("detalhe")
        and t.get("tipo") not in _NOISE_TYPES
    ][:6]

    if eventos_filtrados:
        partes_crono = []
        for t in eventos_filtrados:
            tipo_label = _LABEL_MAP.get(t.get("tipo", ""), t.get("tipo", ""))
            detalhe = _strip_html(t.get("detalhe", ""))
            # Evita detalhe muito longo ou igual ao tipo
            detalhe_curto = _truncate(detalhe, 80) if detalhe and detalhe.lower() != tipo_label else ""
            if detalhe_curto:
                partes_crono.append(f"em {t['data']}, {tipo_label} ({detalhe_curto})")
            else:
                partes_crono.append(f"em {t['data']}, {tipo_label}")
        cronologia = (
            f"Os principais marcos registrados foram: "
            + "; ".join(partes_crono) + "."
        )
    elif imp.get("data_inicio_efetivo") and imp.get("data_inicio_efetivo") != "Nao iniciada":
        cronologia = (
            f"A implantação teve início efetivo em {imp.get('data_inicio_efetivo')} "
            f"e está em andamento há {dias_label}. Não foram registrados eventos adicionais de marcos na timeline."
        )
    else:
        cronologia = (
            f"A implantação está em andamento há {dias_label}. "
            "Nenhum evento de marco foi registrado na timeline até o momento."
        )

    if grupos:
        concluidos_grupos = [g for g in grupos if g["percentual"] == 100]
        em_andamento_grupos = [g for g in grupos if 0 < g["percentual"] < 100]
        nao_iniciados = [g for g in grupos if g["percentual"] == 0 and g["total"] > 0]
        partes = []
        if concluidos_grupos:
            partes.append("fase(s) concluída(s): " + ", ".join(g["titulo"] for g in concluidos_grupos))
        if em_andamento_grupos:
            detalhes = "; ".join(
                f"{g['titulo']} ({g['concluidos']}/{g['total']}, {g['percentual']}%)"
                for g in em_andamento_grupos
            )
            partes.append("em andamento: " + detalhes)
        if nao_iniciados:
            partes.append("ainda não iniciada(s): " + ", ".join(g["titulo"] for g in nao_iniciados))
        andamento = "O progresso está distribuído da seguinte forma — " + "; ".join(partes) + "."
    else:
        pendentes = prog.get("pendentes", 0)
        andamento = (
            f"O progresso geral é de {pct}%, com {concluidos} itens concluídos e "
            f"{pendentes} ainda em aberto."
        )

    overdue = pend.get("overdue_itens", [])
    upcoming = pend.get("upcoming_itens", [])
    pend_parts = []
    if overdue:
        nomes = ", ".join(i["titulo"] for i in overdue[:4])
        pend_parts.append(
            f"{len(overdue)} tarefa(s) com prazo vencido ({nomes})"
        )
    if upcoming:
        pend_parts.append(f"{len(upcoming)} tarefa(s) com prazo nos próximos 7 dias")
    for r in riscos:
        pend_parts.append(r)
    if pend_parts:
        pendencias = "Os pontos de atenção identificados são: " + "; ".join(pend_parts) + "."
    else:
        pendencias = "Nenhuma pendência crítica identificada no momento. O processo segue dentro do esperado."

    proximos_parts = []
    if pend.get("overdue_total", 0) > 0:
        proximos_parts.append(f"regularizar as {pend['overdue_total']} tarefa(s) com prazo vencido")
    if pend.get("upcoming_total", 0) > 0:
        proximos_parts.append(f"acompanhar as {pend['upcoming_total']} tarefa(s) com prazo nos próximos 7 dias")
    if imp.get("status") == "parada":
        proximos_parts.append("retomar o processo e realinhar o cronograma com o cliente")
    if not imp.get("data_finalizacao") and pct >= 80:
        proximos_parts.append("agendar reunião de validação final com o cliente para concluir a implantação")
    if not proximos_parts:
        proximos_parts = [
            "validar prazos e responsáveis das tarefas em aberto com o cliente",
            "manter os registros e evidências atualizados nas tarefas",
        ]
    proximos = "As próximas ações recomendadas são: " + "; ".join(proximos_parts) + "."

    return (
        f"**Resumo Executivo**\n{resumo}\n\n"
        f"**Como chegamos até aqui**\n{cronologia}\n\n"
        f"**Onde estamos hoje**\n{andamento}\n\n"
        f"**Pendências e Riscos**\n{pendencias}\n\n"
        f"**Próximos Passos**\n{proximos}"
    )


def _structured_fallback(context: dict[str, Any]) -> dict[str, Any]:
    imp = context.get("implantacao", {})
    prog = context.get("progresso", {})
    pend = context.get("pendencias", {})
    riscos = context.get("riscos", [])
    timeline = context.get("timeline", [])
    grupos = context.get("checklist_grupos", [])
    comentarios_tarefas = context.get("comentarios_tarefas", [])
    comentarios_total = context.get("comentarios_total", 0)
    anexos = context.get("anexos_recentes", [])

    empresa = imp.get("nome_empresa", "N/A")
    status = imp.get("status", "N/A")
    cs = imp.get("cs_responsavel", "N/A")
    dias = imp.get("dias_em_andamento")
    dias_label = f"{dias} dias" if dias is not None else "N/A"

    # Resumo executivo
    resumo_parts = [f"Implantacao de {empresa} sob responsabilidade de {cs}, atualmente com status '{status}'."]
    if imp.get("data_inicio_efetivo") and imp.get("data_inicio_efetivo") != "Nao informado":
        resumo_parts.append(f"Iniciada em {imp['data_inicio_efetivo']}, com previsao de termino em {imp.get('data_previsao_termino', 'N/A')}.")
    resumo_parts.append(
        f"Progresso atual: {prog.get('percentual', 0)}% ({prog.get('concluidos', 0)}/{prog.get('total_itens', 0)} itens concluidos)."
    )

    # Cronologia a partir da timeline (detalhe ja limpo de HTML em _build_context)
    cronologia_bullets = [
        f"{t['data']} — {t['tipo']}: {_strip_html(t['detalhe'])}"
        for t in timeline[:15]
        if t.get("tipo") and t.get("detalhe")
    ] or ["Nenhum evento registrado na timeline."]

    # Tarefas por grupo
    grupos_bullets = [
        f"{g['titulo']}: {g['concluidos']}/{g['total']} concluidos ({g['percentual']}%)"
        for g in grupos
    ] or [f"Progresso geral: {prog.get('percentual', 0)}% ({prog.get('concluidos', 0)}/{prog.get('total_itens', 0)} itens)."]

    # Pendencias e riscos
    pend_bullets: list[str] = []
    for i in pend.get("overdue_itens", [])[:6]:
        dias_atraso = i.get("dias_atraso", "?")
        pend_bullets.append(f"[ATRASADO {dias_atraso}d] {i['titulo']} — {i['responsavel']}")
    for i in pend.get("upcoming_itens", [])[:4]:
        pend_bullets.append(f"[Vence em breve] {i['titulo']} — {i['responsavel']} (prazo: {i['prazo_fim']})")
    for r in riscos:
        pend_bullets.append(f"[Alerta] {r}")
    if not pend_bullets:
        pend_bullets = ["Nenhuma pendencia critica identificada."]

    pend_text = (
        f"{pend.get('total_abertas', 0)} tarefas abertas, {pend.get('overdue_total', 0)} atrasadas, "
        f"{pend.get('upcoming_total', 0)} vencem nos proximos 7 dias."
    )

    # Comentarios
    comentarios_text = _build_comments_overview(comentarios_tarefas, company_name=empresa)

    # Proximo passos baseados nos dados reais
    proximos: list[str] = []
    if pend.get("overdue_total", 0) > 0:
        proximos.append(f"Regularizar as {pend['overdue_total']} tarefa(s) com prazo vencido.")
    if pend.get("upcoming_total", 0) > 0:
        proximos.append(f"Acompanhar as {pend['upcoming_total']} tarefa(s) com prazo nos proximos 7 dias.")
    if imp.get("status") == "parada":
        proximos.append("Retomar o processo de implantacao e alinhar novo cronograma com o cliente.")
    if not imp.get("data_finalizacao") and prog.get("percentual", 0) >= 80:
        proximos.append("Agendar reuniao de validacao final com o cliente para concluir a implantacao.")
    if comentarios_total == 0:
        proximos.append("Registrar comentarios e evidencias nas tarefas para manter historico atualizado.")
    if not proximos:
        proximos = [
            "Validar prazos e responsaveis das tarefas abertas com o cliente.",
            "Manter registros de reunioes e treinamentos nas tarefas correspondentes.",
        ]

    sections = [
        {
            "title": "Resumo Executivo",
            "text": " ".join(resumo_parts),
            "bullets": [],
        },
        {
            "title": "Cronologia",
            "text": "Principais eventos registrados na implantacao em ordem cronologica.",
            "bullets": cronologia_bullets,
        },
        {
            "title": "Tarefas e Progresso",
            "text": f"Visao do andamento por fase/grupo. Total: {prog.get('total_itens', 0)} itens, {prog.get('pendentes', 0)} ainda abertos.",
            "bullets": grupos_bullets,
        },
        {
            "title": "Pendencias e Riscos",
            "text": pend_text,
            "bullets": pend_bullets,
        },
        {
            "title": "Comentarios e Reunioes",
            "text": comentarios_text,
            "bullets": [],
        },
        {
            "title": "Proximos Passos",
            "text": "",
            "bullets": proximos,
        },
    ]

    return {
        "header": {
            "title": "Relatorio de Implantacao",
            "subtitle": "Documento executivo de acompanhamento",
            "empresa": empresa,
            "status": status,
            "metrics": [
                {"label": "Progresso", "value": f"{prog.get('percentual', 0)}%"},
                {"label": "Itens", "value": f"{prog.get('concluidos', 0)}/{prog.get('total_itens', 0)}"},
                {"label": "Dias em andamento", "value": dias_label},
                {"label": "Tarefas atrasadas", "value": str(pend.get("overdue_total", 0))},
            ],
        },
        "sections": sections,
    }


def _structured_to_text(structured: dict[str, Any]) -> str:
    sections = structured.get("sections", [])
    lines = []
    for sec in sections:
        title = sec.get("title", "Secao")
        text = (sec.get("text") or "").strip()
        bullets = sec.get("bullets") or []
        line = f"{title}: {text}" if text else f"{title}:"
        if bullets:
            line += " " + "; ".join([str(b) for b in bullets[:5]])
        lines.append(line)
    return "\n".join(lines)


def _build_kpi_header(context: dict[str, Any]) -> dict[str, Any]:
    """Retorna apenas o header com KPIs para exibicao no modal."""
    imp = context.get("implantacao", {})
    prog = context.get("progresso", {})
    pend = context.get("pendencias", {})
    dias = imp.get("dias_em_andamento")
    return {
        "empresa": imp.get("nome_empresa", "N/A"),
        "status": imp.get("status", "N/A"),
        "metrics": [
            {"label": "Progresso", "value": f"{prog.get('percentual', 0)}%"},
            {"label": "Itens", "value": f"{prog.get('concluidos', 0)}/{prog.get('total_itens', 0)}"},
            {"label": "Dias em andamento", "value": f"{dias} dias" if dias is not None else "N/A"},
            {"label": "Tarefas atrasadas", "value": str(pend.get("overdue_total", 0))},
        ],
    }


def gerar_resumo_implantacao_service(
    impl_id: int,
    user_email: str | None = None,
    perfil_acesso: str | None = None,
) -> dict[str, Any]:
    is_manager = bool(perfil_acesso in PERFIS_COM_GESTAO) if perfil_acesso else False
    try:
        context = _build_context(impl_id, user_email, is_manager)
    except Exception:
        logger.exception("Unhandled exception", exc_info=True)
        context = _build_minimal_context(impl_id, user_email, is_manager)

    prompt = _build_prompt(context)
    narrative: str | None = None
    source = "gemini"

    try:
        raw = generate_text(prompt).strip()
        # Remove blocos de codigo markdown, se o modelo insistir
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*", "", raw, flags=re.IGNORECASE).strip()
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        if len(raw) >= 100:
            narrative = raw
    except GeminiClientError:
        pass
    except Exception:
        logger.exception("Unhandled exception", exc_info=True)

    if not narrative:
        narrative = _narrative_fallback(context)
        source = "fallback"

    kpi_header = _build_kpi_header(context)

    return {
        "summary": narrative,
        "summary_structured": {"header": kpi_header, "narrative": narrative},
        "source": source,
    }