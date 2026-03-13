from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from .base import Base


class TagSistema(Base):
    __tablename__ = "tags_sistema"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    ordem = Column(Integer, default=0)
    tipo = Column(String(20), default="ambos")
    ativo = Column(Boolean, default=True)

class StatusImplantacao(Base):
    __tablename__ = "status_implantacao"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), nullable=False, unique=True)
    nome = Column(String(100), nullable=False)
    cor = Column(String(30), default="#6c757d")
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)

class NivelAtendimento(Base):
    __tablename__ = "niveis_atendimento"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), nullable=False, unique=True)
    descricao = Column(String(255), nullable=False)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)

class TipoEvento(Base):
    __tablename__ = "tipos_evento"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), nullable=False, unique=True)
    nome = Column(String(100), nullable=False)
    icone = Column(String(50), default="")
    cor = Column(String(30), default="#6c757d")
    ativo = Column(Boolean, default=True)

class MotivoParada(Base):
    __tablename__ = "motivos_parada"
    id = Column(Integer, primary_key=True)
    descricao = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)

class MotivoCancelamento(Base):
    __tablename__ = "motivos_cancelamento"
    id = Column(Integer, primary_key=True)
    descricao = Column(String(255), nullable=False)
    ativo = Column(Boolean, default=True)

class GamificacaoRegra(Base):
    """
    Regras de pontuação de gamificação por contexto (onboarding, ongoing, grandes_contas).
    UNIQUE(regra_id, contexto).
    """
    __tablename__ = "gamificacao_regras"

    id = Column(Integer, primary_key=True)
    regra_id = Column(Text, nullable=False)
    contexto = Column(Text, nullable=False)
    categoria = Column(Text)
    descricao = Column(Text)
    valor_pontos = Column(Integer, default=0)
    tipo_valor = Column(Text, default="pontos")
    ativo = Column(Boolean, default=True)

class PerfilAcesso(Base):
    __tablename__ = "perfis_acesso"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)
    descricao = Column(Text)
    sistema = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    cor = Column(String(20), default="#667eea")
    icone = Column(String(50), default="bi-person-badge")
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = Column(String(100))

class Recurso(Base):
    __tablename__ = "recursos"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(100), unique=True, nullable=False)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    categoria = Column(String(100), nullable=False)
    tipo = Column(String(50), default="acao")
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)

class Permissao(Base):
    __tablename__ = "permissoes"
    id = Column(Integer, primary_key=True)
    perfil_id = Column(Integer, ForeignKey("perfis_acesso.id", ondelete="CASCADE"))
    recurso_id = Column(Integer, ForeignKey("recursos.id", ondelete="CASCADE"))
    concedida = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    """
    Auditoria de ações.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255))
    action = Column(String(100))
    target_type = Column(String(100))
    target_id = Column(String(100))
    changes = Column(Text)
    metadata = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class PerfilUsuarioContexto(Base):
    """
    Perfis de acesso contextuais por módulo (onboarding, ongoing, grandes_contas).
    """
    __tablename__ = "perfil_usuario_contexto"

    usuario = Column(Text, primary_key=True)
    contexto = Column(String(50), primary_key=True)
    perfil_acesso = Column(Text)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = Column(Text)


class ImplantacaoJiraLink(Base):
    """
    Vínculos de tickets Jira com implantações.
    """
    __tablename__ = "implantacao_jira_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    implantacao_id = Column(Integer, ForeignKey("implantacoes.id", ondelete="CASCADE"), nullable=False)
    jira_key = Column(String(20), nullable=False)
    data_vinculo = Column(DateTime, default=datetime.utcnow)
    vinculado_por = Column(Text)


class SmtpSettings(Base):
    """
    Configurações de servidor SMTP.
    """
    __tablename__ = "smtp_settings"

    usuario_email = Column(Text, primary_key=True)
    host = Column(Text, nullable=False)
    port = Column(Integer, nullable=False)
    user = Column(Text)
    password = Column(Text)
    use_tls = Column(Integer, default=1)
    use_ssl = Column(Integer, default=0)


class PerfilUsuario(Base):
    """
    Perfil base do usuário CS (informações gerais, independente de contexto).
    """
    __tablename__ = "perfil_usuario"

    usuario = Column(Text, primary_key=True)  # email do usuário
    nome = Column(Text)
    ultimo_check_externo = Column(DateTime)
    criado_em = Column(DateTime, default=datetime.utcnow)


class ComentarioHistorico(Base):
    """
    Comentários em tarefas do checklist e implantações.
    """
    __tablename__ = "comentarios_h"

    id = Column(Integer, primary_key=True, autoincrement=True)
    implantacao_id = Column(Integer, ForeignKey("implantacoes.id", ondelete="CASCADE"))
    checklist_item_id = Column(Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"))
    usuario_cs = Column(Text)
    texto = Column(Text, nullable=False)
    visibilidade = Column(Text, default="interno")  # interno / externo
    noshow = Column(Boolean, default=False)
    tag = Column(Text)  # ex: "Ação interna", "Reunião", "No Show"
    imagem_url = Column(Text)
    data_criacao = Column(DateTime, default=datetime.utcnow)


class GamificacaoMetricasMensais(Base):
    """
    Métricas mensais para gamificação.
    """
    __tablename__ = "gamificacao_metricas_mensais"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_cs = Column(Text, nullable=False)
    mes = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    nota_qualidade = Column(Float, default=0)
    assiduidade = Column(Float, default=0)
    planos_sucesso_perc = Column(Float, default=0)
    reclamacoes = Column(Integer, default=0)
    perda_prazo = Column(Integer, default=0)
    pontuacao_calculada = Column(Float, default=0)
    elegivel = Column(Boolean, default=False)
    contexto = Column(String(50), default="onboarding")
