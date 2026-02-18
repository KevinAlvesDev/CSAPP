from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

from ....common.dataloader import ChecklistDataLoader
from ....common.utils import format_date_br
from ....constants import PERFIS_COM_GESTAO
from ....db import query_db
from ....modules.checklist.domain.comments import listar_comentarios_implantacao
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
    total_items = loader.total_items
    completed_items = loader.completed_items
    progress_pct = loader.progress_percentage

    pending_items: list[dict[str, Any]] = []
    overdue_items: list[dict[str, Any]] = []
    upcoming_items: list[dict[str, Any]] = []

    now = datetime.now()
    upcoming_limit = now + timedelta(days=7)
    leaf_types = {"tarefa", "subtarefa"}

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

    comments_data = listar_comentarios_implantacao(impl_id, page=1, per_page=60)
    comments = comments_data.get("comments", [])
    recent_comments = [
        {
            "id": c.get("id"),
            "autor": c.get("usuario_nome") or c.get("usuario_cs"),
            "texto": _truncate(c.get("texto") or "", 240),
            "tag": c.get("tag"),
            "data": c.get("data_criacao"),
            "imagem_url": c.get("imagem_url"),
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
        "riscos": riscos,
        "metadados": {
            "gerado_por": user_email,
            "is_manager": is_manager,
        },
    }


def _build_prompt(context: dict[str, Any]) -> str:
    return (
        "Voce e um assistente que gera relatorios claros e objetivos para CS Onboarding.\n"
        "Gere um resumo da implantacao em portugues, com as secoes abaixo.\n"
        "Use linguagem profissional, sem inventar dados. Se algo nao existir, indique como 'Nao informado'.\n\n"
        "Secoes obrigatorias:\n"
        "1. Resumo executivo (3-5 linhas)\n"
        "2. Andamento atual (progresso, status e marcos)\n"
        "3. Pendencias e prazos (inclua atrasos e proximos 7 dias)\n"
        "4. Riscos/Pontos criticos\n"
        "5. Ultimos eventos relevantes\n"
        "6. Proximos passos sugeridos\n\n"
        "Dados estruturados (JSON):\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )


def _fallback_summary(context: dict[str, Any]) -> str:
    imp = context.get("implantacao", {})
    prog = context.get("progresso", {})
    pend = context.get("pendencias", {})
    riscos = context.get("riscos", [])
    timeline = context.get("timeline", [])

    lines = []
    lines.append(
        f"Resumo executivo: Implantaçao de {imp.get('nome_empresa', 'N/A')} em status "
        f"{imp.get('status', 'N/A')}."
    )
    lines.append(
        f"Andamento: {prog.get('percentual', 0)}% ({prog.get('concluidos', 0)}/{prog.get('total_itens', 0)} itens)."
    )
    lines.append(
        f"Pendencias: {pend.get('total', 0)} abertas, "
        f"{pend.get('overdue_total', 0)} atrasadas, "
        f"{pend.get('upcoming_total', 0)} nos proximos 7 dias."
    )
    if riscos:
        lines.append("Riscos: " + "; ".join(riscos))
    else:
        lines.append("Riscos: Nenhum critico identificado.")

    if timeline:
        last = timeline[0]
        lines.append(
            "Ultimo evento: "
            f"{last.get('tipo_evento', 'N/A')} - {last.get('detalhes', '')}"
        )
    else:
        lines.append("Ultimos eventos: Nao informado.")

    lines.append("Proximos passos sugeridos: revisar pendencias e validar prazos com o cliente.")

    return "\n".join(lines)


def gerar_resumo_implantacao_service(
    impl_id: int,
    user_email: str | None = None,
    perfil_acesso: str | None = None,
) -> dict[str, Any]:
    is_manager = bool(perfil_acesso in PERFIS_COM_GESTAO) if perfil_acesso else False
    context = _build_context(impl_id, user_email, is_manager)
    prompt = _build_prompt(context)

    try:
        summary_text = generate_text(prompt)
        source = "gemini"
    except GeminiClientError:
        summary_text = _fallback_summary(context)
        source = "fallback"

    return {
        "summary": summary_text,
        "source": source,
    }
