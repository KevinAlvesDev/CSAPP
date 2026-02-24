from urllib.parse import urlparse

from flask import g, redirect, request, session, url_for

VALID_CONTEXTS = {"onboarding", "grandes_contas", "ongoing"}


def normalize_context(value):
    if not value:
        return None

    context = str(value).strip().lower()
    aliases = {
        "grandes-contas": "grandes_contas",
        "grandescontas": "grandes_contas",
        "gc": "grandes_contas",
        "on-boarding": "onboarding",
        "onboard": "onboarding",
    }
    context = aliases.get(context, context)
    return context if context in VALID_CONTEXTS else None


def context_from_path(path):
    raw = (path or "").strip().lower()
    if not raw:
        return None

    if "://" in raw:
        raw = (urlparse(raw).path or "").lower()

    if raw.startswith("/grandes-contas") or raw.startswith("/grandes_contas"):
        return "grandes_contas"
    if raw.startswith("/ongoing"):
        return "ongoing"
    if raw.startswith("/onboarding"):
        return "onboarding"
    return None


def detect_current_context():
    context = normalize_context(request.args.get("context"))
    if context:
        return context

    context = normalize_context(request.form.get("context"))
    if context:
        return context

    if request.blueprint in ("onboarding", "grandes_contas", "ongoing"):
        return request.blueprint

    context = context_from_path(request.path)
    if context:
        return context

    context = normalize_context(session.get("modulo_atual"))
    if context:
        return context

    context = context_from_path(request.headers.get("Referer", ""))
    if context:
        return context

    return "onboarding"


def persist_current_context():
    context = detect_current_context()
    g.modulo_atual = context
    session["modulo_atual"] = context
    return context


def get_current_dashboard_endpoint(context=None):
    ctx = normalize_context(context) or normalize_context(getattr(g, "modulo_atual", None)) or "onboarding"
    if ctx == "grandes_contas":
        return "grandes_contas.dashboard"
    if ctx == "ongoing":
        return "ongoing.dashboard"
    return "onboarding.dashboard"


def redirect_to_current_dashboard(context=None):
    return redirect(url_for(get_current_dashboard_endpoint(context)))
