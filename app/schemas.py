from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["aberto", "em_atendimento", "resolvido", "fechado", "cancelado"]
Prioridade = Literal["baixa", "media", "alta", "critica"]


class ChamadoCreate(BaseModel):
    titulo: str = Field(min_length=5, max_length=200)
    prioridade: Prioridade = "media"
    area_id: Optional[int] = None
    solicitante_id: Optional[int] = None   # se ausente, assume o colaborador vinculado ao usuário logado
    agente_id: Optional[int] = None


class ChamadoUpdate(BaseModel):
    """Atualizações que NÃO mudam o estado (título, prioridade, área, agente)."""
    titulo: Optional[str] = Field(default=None, min_length=5, max_length=200)
    prioridade: Optional[Prioridade] = None
    area_id: Optional[int] = None
    agente_id: Optional[int] = None


class ChamadoTransicao(BaseModel):
    novo_status: Status


class ChamadoOut(BaseModel):
    """PADRÃO: o modelo de saída NUNCA herda os campos sensíveis/internos."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    status: Status
    prioridade: Prioridade
    area_id: Optional[int]
    solicitante_id: int
    agente_id: Optional[int]
    criado_em: datetime
    resolvido_em: Optional[datetime]
    min_ate_resposta: Optional[int]
    min_ate_resolucao: Optional[int]