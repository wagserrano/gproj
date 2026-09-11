from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import (Chamado, Comunicacao, Material, Mudanca,
                      Participante, Treinamento, TreinamentoTecnologia)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/kpis")
def kpis(
    ini: date = Query(...),
    fim: date = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    chamados = db.execute(
        select(func.count(Chamado.id), func.avg(Chamado.min_ate_resolucao) / 60.0)
        .where(Chamado.criado_em >= ini, Chamado.criado_em < fim)
    ).one()

    trein = db.execute(
        select(func.count(Treinamento.id),
               func.coalesce(func.sum(Treinamento.carga_horaria_h), 0.0))
        .where(Treinamento.data_realizacao >= ini, Treinamento.data_realizacao < fim)
    ).one()

    part = db.execute(
        select(func.count(func.distinct(Participante.colaborador_id)),
               func.avg(Participante.nota_reacao),
               func.avg(Participante.nota_pos - Participante.nota_pre))
        .join(Treinamento, Treinamento.id == Participante.treinamento_id)
        .where(Treinamento.data_realizacao >= ini, Treinamento.data_realizacao < fim)
    ).one()

    tec = db.execute(
        select(func.count(func.distinct(TreinamentoTecnologia.tecnologia_id)))
        .join(Treinamento, Treinamento.id == TreinamentoTecnologia.treinamento_id)
        .where(Treinamento.data_realizacao >= ini, Treinamento.data_realizacao < fim)
    ).scalar_one()

    areas = db.execute(
        select(Chamado.area_id).where(Chamado.criado_em >= ini, Chamado.criado_em < fim)
        .union(select(Treinamento.area_id).where(
            Treinamento.data_realizacao >= ini, Treinamento.data_realizacao < fim))
        .union(select(Mudanca.area_id).where(
            Mudanca.implantada_em >= ini, Mudanca.implantada_em < fim))
    ).scalars().all()

    def _count(model, col, ini, fim):
        return db.scalar(
            select(func.count(model.id)).where(col >= ini, col < fim)
        )

    return {
        "chamados": chamados[0],
        "sla_medio_h": round(chamados[1] or 0, 1),
        "treinamentos": trein[0],
        "horas_ministradas": trein[1],
        "pessoas_capacitadas": part[0],
        "satisfacao_media": round(part[1] or 0, 2),
        "eficacia_ganho": round(part[2] or 0, 1),
        "tecnologias_treinadas": tec,
        "areas_atendidas": len({a for a in areas if a is not None}),
        "materiais_produzidos": _count(Material, Material.publicado_em, ini, fim),
        "comunicacoes_realizadas": _count(Comunicacao, Comunicacao.enviada_em, ini, fim),
        "mudancas_implantadas": _count(Mudanca, Mudanca.implantada_em, ini, fim),
    }