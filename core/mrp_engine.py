# meu_sistema_pcp/core/mrp_engine.py
from sqlalchemy.orm import Session
from database.models import Material, BOM, Inventory


def _estoque_total(db: Session, material_id: int) -> float:
    """Soma o estoque de todos os lotes de um material."""
    lotes = db.query(Inventory).filter(Inventory.material_id == material_id).all()
    return sum(l.current_stock for l in lotes)


def _explodir_componentes(db: Session, material: Material, necessidade_liquida: float, nivel: int, resultado: list, visitados: set):
    """Explode recursivamente os componentes de um material via BOM, com trava antiloop."""
    if material.id in visitados:
        return  # Trava antiloop (evita BOM circular)
    visitados.add(material.id)

    bom_items = db.query(BOM).filter(BOM.parent_material_id == material.id).all()

    for item in bom_items:
        componente = db.query(Material).filter(Material.id == item.child_material_id).first()
        if not componente:
            continue

        nec_bruta = necessidade_liquida * item.qty_required
        estoque_atual = _estoque_total(db, componente.id)
        nec_liquida = max(0.0, nec_bruta - estoque_atual + componente.safety_stock)

        resultado.append({
            "nivel": nivel,
            "material": componente.material_code,
            "descricao": componente.description,
            "necessidade_bruta": round(nec_bruta, 2),
            "estoque_atual": round(estoque_atual, 2),
            "necessidade_liquida": round(nec_liquida, 2),
            "acao_sugerida": "Criar OP" if componente.material_type in ("FERT", "HALB") and nec_liquida > 0
                              else ("Gerar Solicitacao Compra" if nec_liquida > 0 else "Estoque Suficiente")
        })

        # Continua explodindo se o componente também tiver sub-componentes (multi-nível)
        if nec_liquida > 0:
            _explodir_componentes(db, componente, nec_liquida, nivel + 1, resultado, visitados)


def processar_calculo_mrp(codigo_material: str, quantidade: float, db: Session):
    """
    Calcula a explosão de necessidades (MRP) para um material FERT/HALB,
    considerando estoque de segurança e somando todos os lotes existentes.
    """
    mat_alvo = db.query(Material).filter(Material.material_code == codigo_material).first()
    if not mat_alvo:
        return None

    estoque_atual = _estoque_total(db, mat_alvo.id)
    nec_bruta = quantidade
    nec_liquida = max(0.0, nec_bruta - estoque_atual + mat_alvo.safety_stock)

    resultado = [{
        "nivel": 0,
        "material": mat_alvo.material_code,
        "descricao": mat_alvo.description,
        "necessidade_bruta": round(nec_bruta, 2),
        "estoque_atual": round(estoque_atual, 2),
        "necessidade_liquida": round(nec_liquida, 2),
        "acao_sugerida": "Criar OP" if nec_liquida > 0 else "Estoque Suficiente"
    }]

    if nec_liquida > 0:
        _explodir_componentes(db, mat_alvo, nec_liquida, nivel=1, resultado=resultado, visitados={mat_alvo.id})

    return resultado