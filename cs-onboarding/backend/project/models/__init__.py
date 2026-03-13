from datetime import datetime



from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship



from .base import Base





class Usuario(Base):

    """

    Modelo mapeado para a tabela `usuario` já existente no banco de dados OAMD (schema public).

    Compartilhada entre diversos sistemas.

    """

    __tablename__ = "usuario"




    codigo = Column(Integer, primary_key=True)

    nome = Column(String(255))

    email = Column(String(255))

    senha = Column(String(255))

    ativo = Column(Boolean)

    username = Column(String(255))

    perfil_codigo = Column(Integer)

    cargo = Column(String)

    foto_url = Column(String)

    ultimo_check_externo = Column(DateTime)

    auth0_user_id = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



    # Relacionamentos

    # implantacoes = relationship("Implantacao", back_populates="usuario_responsavel")





class EmpresaFinanceiro(Base):

    """

    Modelo mapeado para a tabela `public.empresafinanceiro` no OAMD.

    """

    __tablename__ = "empresafinanceiro"




    codigo = Column(Integer, primary_key=True)

    cnpj = Column(String(20))

    nomefantasia = Column(String(255))

    razaosocial = Column(String(255))

    grupofavorecido = Column(String(255))



    # Relacionamentos

    # implantacoes = relationship("Implantacao", back_populates="empresa")





class Implantacao(Base):

    __tablename__ = "implantacoes"




    id = Column(Integer, primary_key=True, autoincrement=True)

    # No banco real é usuario_cs (email) e não usuario_codigo

    usuario_cs = Column(Text, nullable=False)

    nome_empresa = Column(Text, nullable=False)

    cnpj = Column(Text)

    

    tipo = Column(Text)

    data_criacao = Column(DateTime, default=datetime.utcnow)

    status = Column(Text, default="nova")

    data_inicio_previsto = Column(DateTime)

    data_inicio_efetivo = Column(DateTime)

    data_parada = Column(DateTime)

    data_finalizacao = Column(DateTime)



    # Referência ao Plano de Sucesso aplicado (OAMD)

    plano_sucesso_id = Column(Integer, ForeignKey("planos_sucesso.id"))



    data_atribuicao_plano = Column(DateTime)

    data_previsao_termino = Column(DateTime)

    email_responsavel = Column(Text)

    responsavel_cliente = Column(Text)

    cargo_responsavel = Column(Text)

    telefone_responsavel = Column(Text)

    data_inicio_producao = Column(DateTime)

    data_final_implantacao = Column(DateTime)

    id_favorecido = Column(Text)

    nivel_receita = Column(Text)

    chave_oamd = Column(Text)

    tela_apoio_link = Column(Text)

    informacao_infra = Column(Text)

    seguimento = Column(Text)

    tipos_planos = Column(Text)

    modalidades = Column(Text)

    horarios_func = Column(Text)

    formas_pagamento = Column(Text)

    diaria = Column(Text)

    freepass = Column(Text)

    alunos_ativos = Column(Integer)

    sistema_anterior = Column(Text)

    importacao = Column(Text)

    recorrencia_usa = Column(Text)

    boleto = Column(Text)

    nota_fiscal = Column(Text)

    catraca = Column(Text)

    facial = Column(Text)

    # Valores podem vir como VARCHAR no DB legacy; manter Text para compatibilidade.
    valor_monetario = Column(Numeric(15, 2))
    valor_atribuido = Column(Numeric(15, 2))
    resp_estrategico_nome = Column(Text)

    resp_onb_nome = Column(Text)

    resp_estrategico_obs = Column(Text)

    contatos = Column(Text)

    motivo_parada = Column(Text)

    data_cancelamento = Column(DateTime)

    motivo_cancelamento = Column(Text)

    comprovante_cancelamento_url = Column(Text)

    definicao_carteira = Column(Text)

    contexto = Column(String(50), default="onboarding")



    # Relacionamentos

    # Removido relacionamento usuario_responsavel por incompatibilidade de FK no DB real

    # empresa = relationship("EmpresaFinanceiro", back_populates="implantacoes")

    plano_sucesso_rel = relationship(

        "PlanoSucesso",

        foreign_keys=[plano_sucesso_id],

        # Dissociado back_populates por existir FK em ambos os lados no OAMD

    )

    checklists = relationship("ChecklistItem", back_populates="implantacao", cascade="all, delete-orphan")

    timeline = relationship("TimelineLog", back_populates="implantacao_ref", cascade="all, delete-orphan")





class PlanoSucesso(Base):

    """

    Modelo mapeado para a tabela `planos_sucesso` no OAMD (instância de um plano para uma empresa).

    """

    __tablename__ = "planos_sucesso"




    codigo = Column(Integer, primary_key=True)

    nome = Column(String(255))

    descricao = Column(Text)

    datainicio = Column(DateTime)

    datafinal = Column(DateTime)

    dataconclusao = Column(DateTime)

    # OAMD usa double precision, Float evita erros de cast

    porcentagemconcluida = Column(Float, default=0.0)

    empresafinanceiro_codigo = Column(Integer, ForeignKey("empresafinanceiro.codigo"))

    # Atenção: a coluna no OAMD tem typo ('pucesso'), mapeamos aqui com o nome real

    modeloplanosucesso_codigo = Column(

        "modeloplanopucesso_codigo", Integer, ForeignKey("planos_sucesso.id")

    )

    # OAMD armazena duracao como text (ex: '30 days')

    duracao = Column(Text)

    criadoem = Column(DateTime, default=datetime.utcnow)

    contexto = Column(String(50), default="onboarding")

    processo_id = Column(Integer, ForeignKey("implantacoes.id"))



    # Relacionamentos

    implantacoes = relationship(

        "Implantacao",

        foreign_keys=[processo_id],

        # Dissociado back_populates por existir FK em ambos os lados no OAMD

    )

    acoes = relationship("PlanoSucessoAcao", back_populates="plano", cascade="all, delete-orphan")





class PlanoSucessoAcao(Base):

    """

    Ações concretas de um Plano de Sucesso em andamento.

    """

    __tablename__ = "planos_sucesso_acoes"




    codigo = Column(Integer, primary_key=True)

    planosucesso_codigo = Column(Integer, ForeignKey("planos_sucesso.id"))

    nome = Column(String(255))

    ordem = Column(Integer)

    situacao = Column(String(50))

    datasituacao = Column(DateTime)

    concluidopor = Column(String(255))

    contexto = Column(String(50), default="onboarding")



    # Relacionamentos

    plano = relationship("PlanoSucesso", back_populates="acoes")





class ModeloPlanoSucesso(Base):

    """

    Templates de Planos de Sucesso (Ex: Onboarding Musculação, etc).

    """

    __tablename__ = "planos_sucesso"




    codigo = Column(Integer, primary_key=True)

    nome = Column(String(255), nullable=False)

    descricao = Column(Text)

    duracao = Column(Integer) # em dias

    contexto = Column(String(100))

    ativo = Column(Boolean, default=True)



    # Relacionamentos

    acoes = relationship("ModeloPlanoSucessoAcao", back_populates="modelo")





class ModeloPlanoSucessoAcao(Base):

    """

    Ações/Tarefas de um Template de Plano de Sucesso.

    """

    __tablename__ = "planos_sucesso_acoes"




    codigo = Column(Integer, primary_key=True)

    modeloplanosucesso_codigo = Column(Integer, ForeignKey("planos_sucesso.id"))

    nome = Column(String(255), nullable=False)

    ordem = Column(Integer, default=0)

    duracao = Column(Integer, default=0)

    notas = Column(Text)

    parent_codigo = Column(Integer, ForeignKey("planos_sucesso_acoes.codigo"))



    # Relacionamentos

    modelo = relationship("ModeloPlanoSucesso", back_populates="acoes")

    subacoes = relationship("ModeloPlanoSucessoAcao", back_populates="pai")

    pai = relationship("ModeloPlanoSucessoAcao", back_populates="subacoes", remote_side=[codigo])





class ChecklistItem(Base):

    __tablename__ = "checklist_items"




    id = Column(Integer, primary_key=True, autoincrement=True)

    parent_id = Column(Integer, ForeignKey("checklist_items.id", ondelete="CASCADE"))

    title = Column(Text, nullable=False)

    completed = Column(Integer, nullable=False, default=0)

    comment = Column(Text)

    level = Column(Integer, default=0)

    ordem = Column(Integer, default=0)

    implantacao_id = Column(Integer, ForeignKey("implantacoes.id"))

    plano_id = Column(Integer)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    responsavel = Column(Text)

    status = Column(Text, default="pendente")

    percentual_conclusao = Column(Integer, default=0)

    obrigatoria = Column(Integer, default=0)

    tipo_item = Column(Text)

    descricao = Column(Text)

    tag = Column(Text)

    data_conclusao = Column(DateTime)

    dispensada = Column(Integer, default=0)

    motivo_dispensa = Column(Text)

    dispensada_por = Column(Text)

    dispensada_em = Column(DateTime)

    dias_offset = Column(Integer)

    dias_uteis = Column(Integer, default=0)

    previsao_original = Column(DateTime)

    nova_previsao = Column(DateTime)

    prazo_inicio = Column(DateTime)

    prazo_fim = Column(DateTime)

    contexto = Column(String(50), default="onboarding")



    # Relacionamentos

    implantacao = relationship("Implantacao", back_populates="checklists")

    filhos = relationship("ChecklistItem", back_populates="pai")

    pai = relationship("ChecklistItem", back_populates="filhos", remote_side=[id])





class TimelineLog(Base):

    __tablename__ = "timeline_log"




    id = Column(Integer, primary_key=True, autoincrement=True)

    implantacao_id = Column(Integer, ForeignKey("implantacoes.id"), nullable=False)

    usuario_cs = Column(Text, nullable=False)

    tipo_evento = Column(Text, nullable=False)

    detalhes = Column(Text)

    data_criacao = Column(DateTime, default=datetime.utcnow)



    # Relacionamentos

    implantacao_ref = relationship("Implantacao", back_populates="timeline")
