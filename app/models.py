from datetime import date, datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Float, ForeignKey, CheckConstraint, func, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

# ---------- Cadastros-base ----------

class Area(Base):
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    sigla: Mapped[Optional[str]] = mapped_column(String)
    ativa: Mapped[bool] = mapped_column(default=True)
    colaboradores: Mapped[List["Colaborador"]] = relationship(back_populates="area")

class Colaborador(Base):
    __tablename__ = "colaboradores"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    ativo: Mapped[bool] = mapped_column(default=True)
    area: Mapped["Area"] = relationship(back_populates="colaboradores")

class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String)
    papel: Mapped[str] = mapped_column(String, default="leitor")   # admin|agente|instrutor|gestor|leitor
    colaborador_id: Mapped[Optional[int]] = mapped_column(ForeignKey("colaboradores.id"))
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ultimo_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

class Tecnologia(Base):
    __tablename__ = "tecnologias"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, unique=True)
    categoria: Mapped[Optional[str]] = mapped_column(String)

# ---------- Treinamentos ----------

class Treinamento(Base):
    __tablename__ = "treinamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String)
    data_realizacao: Mapped[date] = mapped_column(Date, index=True)
    carga_horaria_h: Mapped[float] = mapped_column(Float)
    instrutor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("areas.id"))
    formato: Mapped[str] = mapped_column(String, default="presencial")
    tecnologias: Mapped[List["Tecnologia"]] = relationship(
        secondary="treinamento_tecnologias", back_populates="treinamentos"
    )

class TreinamentoTecnologia(Base):
    __tablename__ = "treinamento_tecnologias"
    treinamento_id: Mapped[int] = mapped_column(
        ForeignKey("treinamentos.id", ondelete="CASCADE"), primary_key=True)
    tecnologia_id: Mapped[int] = mapped_column(
        ForeignKey("tecnologias.id"), primary_key=True)

Tecnologia.treinamentos = relationship(
    "Treinamento", secondary="treinamento_tecnologias", back_populates="tecnologias")

class Participante(Base):
    __tablename__ = "participantes"
    __table_args__ = (
        CheckConstraint("nota_reacao BETWEEN 1 AND 5"),
        CheckConstraint("nota_pre  BETWEEN 0 AND 100"),
        CheckConstraint("nota_pos  BETWEEN 0 AND 100"),
    )
    treinamento_id: Mapped[int] = mapped_column(
        ForeignKey("treinamentos.id", ondelete="CASCADE"), primary_key=True)
    colaborador_id: Mapped[int] = mapped_column(
        ForeignKey("colaboradores.id"), primary_key=True)
    presente: Mapped[bool] = mapped_column(default=False)
    nota_reacao: Mapped[Optional[int]] = mapped_column()   # KPI Satisfação
    nota_pre: Mapped[Optional[int]] = mapped_column()      # KPI Eficácia (opcional)
    nota_pos: Mapped[Optional[int]] = mapped_column()      # KPI Eficácia

# ---------- Atendimento / Mudanças ----------

class Chamado(Base):
    __tablename__ = "chamados"
    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="aberto", index=True)
    prioridade: Mapped[str] = mapped_column(String, default="media")
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("areas.id"))
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("colaboradores.id"))
    agente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True)
    resolvido_em: Mapped[Optional[datetime]] = mapped_column(DateTime)
    min_ate_resposta: Mapped[Optional[int]] = mapped_column()
    min_ate_resolucao: Mapped[Optional[int]] = mapped_column()  # KPI SLA

class Mudanca(Base):
    __tablename__ = "mudancas"
    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="solicitada")
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("areas.id"))
    chamado_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chamados.id"))
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    solicitada_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    implantada_em: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)

# ---------- Produção / Comunicação ----------

class Material(Base):
    __tablename__ = "materiais"
    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String)
    tipo: Mapped[str] = mapped_column(String, default="tutorial")
    url_arquivo: Mapped[str] = mapped_column(String)
    tecnologia_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tecnologias.id"))
    treinamento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("treinamentos.id"))
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    publicado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True)

class Comunicacao(Base):
    __tablename__ = "comunicacoes"
    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String)
    canal: Mapped[str] = mapped_column(String, default="email")
    area_id: Mapped[Optional[int]] = mapped_column(ForeignKey("areas.id"))
    material_id: Mapped[Optional[int]] = mapped_column(ForeignKey("materiais.id"))
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    enviada_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True)