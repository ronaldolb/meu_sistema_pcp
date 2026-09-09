# meu_sistema_pcp/core/shop_floor.py
from database.models import Material, BOM, Inventory, ProductionOrder, BatchGenealogy
from sqlalchemy.orm import Session


def release_production_order(db: Session, op_code: str):
    """
    Simula a Liberação da OP (Check ATP com Lotes).
    Soma o estoque disponível de todos os lotes do componente para validar a liberação.
    """
    print(f"\n>>> [PCP] Iniciando liberação da Ordem com Lote: {op_code}")

    order = db.query(ProductionOrder).filter(ProductionOrder.op_code == op_code).first()
    if not order:
        print("Erro: Ordem de Produção não encontrada no banco.")
        return False

    material = db.query(Material).filter(Material.id == order.material_id).first()
    bom_items = db.query(BOM).filter(BOM.parent_material_id == material.id).all()
    has_all_materials = True

    print("-> Verificando disponibilidade nos lotes de componentes (Check ATP)...")
    for item in bom_items:
        child_material = db.query(Material).filter(Material.id == item.child_material_id).first()
        qty_needed = order.qty_planned * item.qty_required

        total_stock = db.query(Inventory).filter(Inventory.material_id == child_material.id).all()
        stock_available = sum(inv.current_stock for inv in total_stock)

        if stock_available >= qty_needed:
            print(f"   [OK] {child_material.material_code}: Necessário {qty_needed} | Total nos Lotes {stock_available}")
        else:
            print(f"   [FALHA] {child_material.material_code}: Necessário {qty_needed} | Total nos Lotes {stock_available} (FALTA MATERIAL)")
            has_all_materials = False

    if has_all_materials:
        order.status = "REL"
        db.commit()
        print(f"-> [STATUS ALTERADO] Ordem {op_code} alterada para REL (Liberada para Fábrica).")
        return True
    else:
        print(f"-> [BLOQUEADO] Ordem {op_code} não pôde ser liberada por falta de insumos.")
        return False


def confirm_production_order_with_batches(db: Session, op_code: str, qty_produced_good: float, qty_scrap: float, components_batches: dict):
    """
    Apontamento com Rastreabilidade de Lote (Equivalente à CO11N + CHVW do SAP).
    Dá entrada no lote do acabado (Mov 101) e consome lotes específicos de insumos (Mov 261).

    :param components_batches: Dicionário contendo {'CODIGO-COMPONENTE': 'NUMERO-LOTE'}
    """
    print(f"\n>>> [CHÃO DE FÁBRICA] Apontando Produção com Lotes para a Ordem: {op_code}")

    # 1. Validar a ordem
    order = db.query(ProductionOrder).filter(ProductionOrder.op_code == op_code).first()
    if not order or order.status != "REL":
        print("Erro: A ordem precisa estar com status REL (Liberada) para ser apontada.")
        return False

    parent_material = db.query(Material).filter(Material.id == order.material_id).first()
    total_processed = qty_produced_good + qty_scrap

    # Garantir que um lote de produto foi definido (gerado no MRP) e PERSISTIR na ordem
    lote_pai = order.product_batch or f"LOT-FERT-{order.op_code}"
    order.product_batch = lote_pai  # <-- CORREÇÃO: grava o lote gerado de volta na OP

    # 2. ENTRADA DO ACABADO/SEMIACABADO POR LOTE (Movimento 101 SAP)
    inventory_entry = db.query(Inventory).filter(
        Inventory.material_id == parent_material.id,
        Inventory.batch_number == lote_pai
    ).first()

    if inventory_entry:
        inventory_entry.current_stock += qty_produced_good
    else:
        new_inv = Inventory(material_id=parent_material.id, batch_number=lote_pai, current_stock=qty_produced_good)
        db.add(new_inv)

    print(f"-> [Mov 101] Entrada de {qty_produced_good} un no LOTE PAI: {lote_pai} do material {parent_material.material_code}")

    # 3. BAIXA AUTOMÁTICA POR LOTE ESPECÍFICO (Movimento 261 SAP - Backflush por Lote)
    bom_items = db.query(BOM).filter(BOM.parent_material_id == parent_material.id).all()

    for item in bom_items:
        child_material = db.query(Material).filter(Material.id == item.child_material_id).first()
        qty_to_consume = total_processed * item.qty_required

        lote_componente_informado = components_batches.get(child_material.material_code)

        if not lote_componente_informado:
            print(f"Erro Crítico: Lote para o componente {child_material.material_code} não foi informado pelo operador.")
            db.rollback()
            return False

        inventory_comp = db.query(Inventory).filter(
            Inventory.material_id == child_material.id,
            Inventory.batch_number == lote_componente_informado
        ).first()

        if not inventory_comp or inventory_comp.current_stock < qty_to_consume:
            print(f"Erro Crítico: Lote {lote_componente_informado} do componente {child_material.material_code} não possui saldo suficiente ({qty_to_consume} un necessárias).")
            db.rollback()
            return False

        inventory_comp.current_stock -= qty_to_consume
        print(f"-> [Mov 261 - Backflush por Lote] Subtraídas {qty_to_consume} un do LOTE FILHO: {lote_componente_informado} ({child_material.material_code})")

        # 4. GRAVAR REGISTRO DE GENEALOGIA (Rastreabilidade completa)
        genealogy_entry = BatchGenealogy(
            production_order_id=order.id,
            parent_batch=lote_pai,
            component_material_id=child_material.id,
            component_batch=lote_componente_informado,
            qty_consumed=qty_to_consume
        )
        db.add(genealogy_entry)

    # 5. Finalizar e salvar a transação com segurança
    order.status = "CNF"
    order.qty_confirmed = (order.qty_confirmed or 0.0) + qty_produced_good
    db.commit()
    print(f"-> [STATUS ALTERADO] Ordem {op_code} atualizada para CNF. Rastreabilidade gravada com sucesso!")
    return True