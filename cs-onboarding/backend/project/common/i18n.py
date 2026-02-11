from collections.abc import Callable

TRANSLATIONS = {
    "pt": {
        "forgot_title": "Recuperar senha",
        "forgot_subtitle": "Informe seu e-mail para receber o link.",
        "email_label": "E-mail",
        "send_link_button": "Enviar link",
        "back_to_login": "Voltar ao login",
        "reset_title": "Redefinir senha",
        "reset_subtitle": "Escolha uma nova senha para sua conta.",
        "new_password_label": "Nova senha",
        "confirm_new_password_label": "Confirmar nova senha",
        "reset_button": "Redefinir",
        "change_title": "Alterar senha",
        "change_subtitle": "Atualize sua senha com segurança.",
        "current_password_label": "Senha atual",
        "change_button": "Alterar senha",
        "back": "Voltar",
        "forgot_link_text": "Esqueci minha senha",
    },
    "en": {
        "forgot_title": "Forgot password",
        "forgot_subtitle": "Enter your email to receive the link.",
        "email_label": "Email",
        "send_link_button": "Send link",
        "back_to_login": "Back to login",
        "reset_title": "Reset password",
        "reset_subtitle": "Choose a new password for your account.",
        "new_password_label": "New password",
        "confirm_new_password_label": "Confirm new password",
        "reset_button": "Reset",
        "change_title": "Change password",
        "change_subtitle": "Update your password securely.",
        "current_password_label": "Current password",
        "change_button": "Change password",
        "back": "Back",
        "forgot_link_text": "Forgot my password",
    },
}


def get_translator(app) -> Callable[[str], str]:
    def t(key: str, **kwargs) -> str:
        lang = (getattr(app, "config", {}) or {}).get("LANG", "pt")
        table = TRANSLATIONS.get(lang, TRANSLATIONS["pt"])
        text = table.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    return t
