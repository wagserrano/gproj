from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import exigir, get_current_user
from ..database import get_db
from ..models import Chamado, Usuario
from ..schemas import ChamadoCreate, ChamadoOut, ChamadoTransicao, ChamadoUpdate

router = APIRouter(prefix="/chamados", tags=["chamados"])

# ==========================================================================
# PADRÃO 1 — Máquina de estados declarativa (dicionário, não if-else solto)
# ==========================================================================
TRANSICOES_VALIDAS: dict[str, set[str]] = {
    "aberto":          {"em_atendimento", "cancelado"},
    "em_atendimento":  {"resolvido", "aberto", "cancelado"},
    "resolvido":       {"fechado"},
    "fechado":         set(),
    "cancelado":       set(),
}

PAPEIS_OPERACAO = ("agente",)   # admin sempre passa (ver exigir())


def _agora() -> datetime:
    """PADRÃO 2 — UTC naive em todo o sistema.
    SQLite e PG (timestamp sem fuso) retornam datetimes naive; misturar com
    datetime 'aware' quebra a subtração usada no cálculo do SLA."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _minutos(inicio: datetime, fim: datetime) -> int:
    return max(0, int((fim - inicio).total_seconds() // 60))


def _obter(db: Session, chamado_id: int) -> Chamado:
    """PADRÃO 3 — helper de busca com 404 padronizado."""
    chamado = db.get(Chamado, chamado_id)
    if not chamado:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chamado não encontrado")
    return chamado


# ==========================================================================
# CREATE
# ==========================================================================
@router.post("", response_model=ChamadoOut, status_code=status.HTTP_201_CREATED)
def criar_chamado(
    payload: ChamadoCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(exigir(*PAPEIS_OPERACAO)),
):
    # PADRÃO 4 — regra de negócio de preenchimento automático
    solicitante_id = payload.solicitante_id or user.colaborador_id
    if not solicitante_id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Informe solicitante_id ou vincule o usuário a um colaborador",
        )

    chamado = Chamado(
        titulo=payload.titulo,
        prioridade=payload.prioridade,
        area_id=payload.area_id,
        solicitante_id=solicitante_id,
        agente_id=payload.agente_id,
        status="aberto",
    )
    db.add(chamado)
    db.commit()
    db.refresh(chamado)          # popula id e criado_em (server_default)
    return chamado


# ==========================================================================
# READ (lista com filtros + paginação)
# ==========================================================================
@router.get("", response_model=list[ChamadoOut])
def listar_chamados(
    status_f: Optional[str] = Query(None, alias="status"),
    prioridade: Optional[str] = None,
    area_id: Optional[int] = None,
    agente_id: Optional[int] = None,
    q: Optional[str] = Query(None, max_length=100, description="Busca no título"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),   # leitura: qualquer usuário autenticado
):
    stmt = select(Chamado).order_by(Chamado.criado_em.desc())
    # PADRÃO 5 — filtros acumulados condicionalmente
    if status_f:
        stmt = stmt.where(Chamado.status == status_f)
    if prioridade:
        stmt = stmt.where(Chamado.prioridade == prioridade)
    if area_id:
        stmt = stmt.where(Chamado.area_id == area_id)
    if agente_id:
        stmt = stmt.where(Chamado.agente_id == agente_id)
    if q:
        stmt = stmt.where(Chamado.titulo.ilike(f"%{q}%"))   # portável SQLite/PG
    return db.scalars(stmt.offset(skip).limit(limit)).all()


@router.get("/{chamado_id}", response_model=ChamadoOut)
def obter_chamado(
    chamado_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    return _obter(db, chamado_id)


# ==========================================================================
# UPDATE (campos que não alteram estado)
# ==========================================================================
@router.patch("/{chamado_id}", response_model=ChamadoOut)
def atualizar_chamado(
    chamado_id: int,
    payload: ChamadoUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(exigir(*PAPEIS_OPERACAO)),
):
    chamado = _obter(db, chamado_id)
    if chamado.status in ("fechado", "cancelado"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Chamado encerrado não pode ser editado")

    # PADRÃO 6 — update parcial: só os campos enviados
    dados = payload.model_dump(exclude_unset=True)
    for campo, valor in dados.items():
        setattr(chamado, campo, valor)

    db.commit()
    db.refresh(chamado)
    return chamado


# ==========================================================================
# TRANSIÇÃO DE STATUS (regra de negócio + SLA)
# ==========================================================================
@router.patch("/{chamado_id}/status", response_model=ChamadoOut)
def transitar_status(
    chamado_id: int,
    payload: ChamadoTransicao,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    chamado = _obter(db, chamado_id)

    # PADRÃO 7 — autorização refinada dentro da operação:
    # solicitantes (colaborador vinculado) só podem cancelar o próprio chamado
    if user.papel not in (*PAPEIS_OPERACAO, "admin"):
        eh_solicitante = (
            user.colaborador_id is not None
            and user.colaborador_id == chamado.solicitante_id
            and payload.novo_status == "cancelado"
            and chamado.status in ("aberto", "em_atendimento")   # ← SEM o "-" daqui
        )
        if not eh_solicitante:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")

    if payload.novo_status not in TRANSICOES_VALIDAS.get(chamado.status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Transição inválida: '{chamado.status}' → '{payload.novo_status}'",
        )

    agora = _agora()
    # PADRÃO 8 — efeitos colaterais da transição (aqui: SLA)
    if payload.novo_status == "em_atendimento" and chamado.min_ate_resposta is None:
        chamado.min_ate_resposta = _minutos(chamado.criado_em, agora)
    elif payload.novo_status == "resolvido":
        chamado.resolvido_em = agora
        chamado.min_ate_resolucao = _minutos(chamado.criado_em, agora)

    chamado.status = payload.novo_status
    db.commit()
    db.refresh(chamado)
    return chamado


# ==========================================================================
# DELETE — não existe. Encerramento é transição para 'cancelado'/'fechado'
# (soft-delete: preserva histórico para os KPIs). PADRÃO 9.
# ==========================================================================