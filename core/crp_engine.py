# meu_sistema_pcp/core/crp_engine.py
from database.models import WorkCenter, Routing, ProductionOrder, Material

def calculate_work_center_load(db):
    """
    Motor de CRP (Capacity Requirements Planning - Padrão SAP)
    Calcula a carga de horas acumulada nas máquinas blindado contra valores nulos.
    """
    print("\n--- Executando Cálculo de Capacidade e Carga (CRP) ---")
    
    work_centers = db.query(WorkCenter).all()
    capacity_report = {}
    
    for wc in work_centers:
        total_hours_needed = 0.0
        
        # Buscar todas as operações de roteiro associadas a este posto de trabalho
        routings = db.query(Routing).filter(Routing.work_center_id == wc.id).all()
        
        for rot in routings:
            # Buscar OPs que estão ativas e gerando carga de trabalho real nas máquinas
            active_orders = db.query(ProductionOrder).filter(
                ProductionOrder.material_id == rot.material_id,
                ProductionOrder.status.in_(["CRTD", "REL"])
            ).all()
            
            for op in active_orders:
                # Conversão explícita para float para evitar quebras de tipos matemáticos
                qty_planned = float(op.qty_planned or 0.0)
                setup_minutes = float(rot.setup_time_minutes or 0.0)
                processing_minutes = float(rot.processing_time_minutes or 0.0)
                
                # Fórmula de Carga SAP: Setup + (Quantidade x Tempo de Processo)
                setup_hours = setup_minutes / 60.0
                processing_hours = (qty_planned * processing_minutes) / 60.0
                
                total_hours_needed += (setup_hours + processing_hours)
                
        # Calcular o percentual de ocupação baseado no turno diário disponível
        capacity_daily = float(wc.capacity_hours_per_day or 8.0)
        utilization_percentage = 0.0
        if capacity_daily > 0:
            utilization_percentage = (total_hours_needed / capacity_daily) * 100
            
        capacity_report[wc.work_center_code] = {
            "descricao": str(wc.description),
            "horas_requeridas": float(round(total_hours_needed, 2)),
            "capacidade_diaria": float(capacity_daily),
            "percentual_ocupacao": float(round(utilization_percentage, 2))
        }
        
        print(f"-> Posto {wc.work_center_code}: Requer {round(total_hours_needed, 2)}h de {capacity_daily}h ({round(utilization_percentage, 2)}%)")
        
    return capacity_report
