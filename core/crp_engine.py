# meu_sistema_pcp/core/crp_engine.py
from sqlalchemy.orm import Session
from database.models import WorkCenter, Routing, ProductionOrder


def calcular_carga_postos(db: Session):
    """
    Calcula a carga (CRP) de cada posto de trabalho, somando o tempo
    de setup + processamento de todas as ordens abertas (status != CNF)
    que passam por aquele posto, segundo o Roteiro (Routing).
    """
    postos = db.query(WorkCenter).all()
    resultado = []

    for posto in postos:
        roteiros = db.query(Routing).filter(Routing.work_center_id == posto.id).all()
        horas_necessarias = 0.0

        for rot in roteiros:
            ordens_abertas = db.query(ProductionOrder).filter(
                ProductionOrder.material_id == rot.material_id,
                ProductionOrder.status != "CNF"
            ).all()

            for op in ordens_abertas:
                qty_pendente = op.qty_planned - (op.qty_confirmed or 0.0)
                if qty_pendente <= 0:
                    continue
                minutos = rot.setup_time_minutes + (rot.processing_time_minutes * qty_pendente)
                horas_necessarias += minutos / 60.0

        load_pct = round((horas_necessarias / posto.capacity_hours_per_day) * 100, 1) if posto.capacity_hours_per_day > 0 else 0.0

        resultado.append({
            "work_center_code": posto.work_center_code,
            "description": posto.description,
            "capacity_hours_per_day": posto.capacity_hours_per_day,
            "required_hours": round(horas_necessarias, 2),
            "load_percentage": load_pct
        })

    return resultado