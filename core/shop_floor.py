# meu_sistema_pcp/core/shop_floor.py
from database.models import Material, BOM, Inventory, ProductionOrder

def release_production_order(db, op_code):
    """
    Simula a Liberação da OP (Disponibilidade).
    Verifica se há estoque físico dos componentes da BOM antes de permitir a produção.
    """
    print(f"\n>>> [PCP] Iniciando liberação da Ordem no Banco: {op_code}")
    
    # 1. Buscar a ordem de produção
    order = db.query(ProductionOrder).filter(ProductionOrder.op_code == op_code).first()
    if not order:
        print("Erro: Ordem de Produção não encontrada no banco de dados.")
        return False
        
    material = db.query(Material).filter(Material.id == order.material_id).first()
    
    # 2. Buscar componentes da Lista Técnica (BOM)
    bom_items = db.query(BOM).filter(BOM.parent_material_id == material.id).all()
    has_all_materials = True
    
    print("-> Verificando disponibilidade de componentes (Check ATP Real)...")
    for item in bom_items:
        child_material = db.query(Material).filter(Material.id == item.child_material_id).first()
        qty_needed = order.qty_planned * item.qty_required
        
        # Puxa o saldo físico atual do inventário
        stock_available = child_material.inventory.current_stock if child_material.inventory else 0.0
        
        if stock_available >= qty_needed:
            print(f"   [OK] {child_material.material_code}: Necessário {qty_needed} | Disponível {stock_available}")
        else:
            print(f"   [FALHA] {child_material.material_code}: Necessário {qty_needed} | Disponível {stock_available} (FALTA MATERIAL)")
            has_all_materials = False
            
    # 3. Mudar status se houver saldo de todos os insumos
    if has_all_materials:
        order.status = "REL"
        db.commit()
        print(f"-> [STATUS ALTERADO] Ordem {op_code} alterada para REL (Liberada para Fábrica).")
        return True
    else:
        print(f"-> [BLOQUEADO] Ordem {op_code} não pôde ser liberada por falta de insumos.")
        return False


def confirm_production_order(db, op_code, qty_produced_good, qty_scrap):
    """
    Simula o Apontamento e Encerramento (CO11N / Backflush).
    Dá entrada no produto bom (Mov 101) e consome os componentes da BOM (Mov 261).
    """
    print(f"\n>>> [CHÃO DE FÁBRICA] Apontando Produção para a Ordem: {op_code}")
    
    # 1. Validar a ordem
    order = db.query(ProductionOrder).filter(ProductionOrder.op_code == op_code).first()
    if not order or order.status != "REL":
        print("Erro: A ordem precisa estar com status REL (Liberada) para ser apontada.")
        return False
        
    parent_material = db.query(Material).filter(Material.id == order.material_id).first()
    total_processed = qty_produced_good + qty_scrap
    
    # 2. ENTRADA DO ACABADO/SEMIACABADO (Movimento 101 SAP)
    if parent_material.inventory:
        parent_material.inventory.current_stock += qty_produced_good
    else:
        new_inv = Inventory(material_id=parent_material.id, current_stock=qty_produced_good)
        db.add(new_inv)
        
    print(f"-> [Mov 101] Entrada de {qty_produced_good} unidades de {parent_material.material_code} no estoque físico.")
    
    # 3. BAIXA AUTOMÁTICA DOS INSUMOS (Movimento 261 SAP - Backflush)
    bom_items = db.query(BOM).filter(BOM.parent_material_id == parent_material.id).all()
    for item in bom_items:
        child_material = db.query(Material).filter(Material.id == item.child_material_id).first()
        qty_to_consume = total_processed * item.qty_required
        
        if child_material.inventory:
            child_material.inventory.current_stock -= qty_to_consume
            print(f"-> [Mov 261 - Backflush] Subtraídas {qty_to_consume} unidades de {child_material.material_code} do estoque.")
            
    # 4. Finalizar e salvar a transação
    order.status = "CNF"
    order.qty_confirmed = qty_produced_good
    db.commit()
    print(f"-> [STATUS ALTERADO] Ordem {op_code} atualizada para CNF (Confirmada/Encerrada).")
    return True
