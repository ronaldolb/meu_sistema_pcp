# meu_sistema_pcp/core/mrp_engine.py
import math
from datetime import datetime, timedelta
from database.models import Material, BOM, Inventory, ProductionOrder

def run_mrp_for_material(db, material_code, gross_demand, date_needed):
    """
    Motor do MRP Relacional (Padrão SAP)
    Lê dados reais de engenharia e estoque do pcp.db para planejar a produção.
    """
    print(f"\n--- Executando MRP para: {material_code} ---")
    
    # 1. Puxar dados mestres do banco de dados
    material = db.query(Material).filter(Material.material_code == material_code).first()
    if not material:
        print(f"Erro: Material '{material_code}' não encontrado no Mestre de Materiais.")
        return []
    
    # 2. Calcular Estoque Disponível Projetado (Fórmula SAP)
    stock_on_hand = 0.0
    if material.inventory:
        stock_on_hand = material.inventory.current_stock
        
    firm_receipts = db.query(ProductionOrder).filter(
        ProductionOrder.material_id == material.id,
        ProductionOrder.status == "REL"
    ).all()
    total_firm_receipts = sum(op.qty_planned for op in firm_receipts)
    
    available_stock = stock_on_hand + total_firm_receipts
    print(f"-> Estoque Físico: {stock_on_hand} | OPs em Processo (+): {total_firm_receipts}")
    print(f"-> Estoque Disponível Projetado: {available_stock} (Demandado Bruto: {gross_demand})")
    
    # 3. Calcular a Necessidade Líquida considerando o Estoque de Segurança
    net_requirement = gross_demand + material.safety_stock - available_stock
    
    if net_requirement <= 0:
        print(f"-> [OK] Estoque suficiente para manter a segurança de {material.safety_stock} unidades.")
        return []
    
    print(f"-> [ALERTA] Necessidade Líquida: {net_requirement} unidades (Estoque Segurança: {material.safety_stock}).")
    
    # 4. Programação Regressiva de Datas (Backward Scheduling)
    start_date = date_needed - timedelta(days=material.lead_time_days)
    
    # 5. Criar e registrar a Ordem Planejada no Banco de Dados (Status 'CRTD')
    # Adicionamos um carimbo de milissegundos para garantir que o código seja sempre 100% único
    timestamp = datetime.now().strftime('%M%S%f')[:-3]
    op_code_temp = f"OP-PL-{timestamp}-{material.id}"
    
    new_op = ProductionOrder(
        op_code=op_code_temp,
        material_id=material.id,
        qty_planned=float(net_requirement),
        status="CRTD",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=date_needed.strftime("%Y-%m-%d")
    )
    db.add(new_op)
    db.commit()
    db.refresh(new_op) # Garante que o objeto está sincronizado com o banco
    print(f"-> [OP GERADA NO BANCO] {new_op.op_code} | Qtd: {new_op.qty_planned}")
    
    generated_orders = [new_op]
    
    # 6. EXPLOSÃO EM CASCATA DA BOM (Próximo nível da árvore de produtos)
    bom_items = db.query(BOM).filter(BOM.parent_material_id == material.id).all()
    
    if bom_items:
        print(f"-> Explodindo a BOM de {material_code} para suprir as {net_requirement} unidades...")
        for item in bom_items:
            child_material = db.query(Material).filter(Material.id == item.child_material_id).first()
            if child_material:
                comp_gross_demand = net_requirement * item.qty_required
                
                # Executa o MRP recursivamente para as matérias-primas e semiacabados
                child_orders = run_mrp_for_material(db, child_material.material_code, comp_gross_demand, start_date)
                generated_orders.extend(child_orders)
                
    return generated_orders
