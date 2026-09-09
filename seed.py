# meu_sistema_pcp/seed.py
from database.connection import SessionLocal, init_db
from database.models import Material, BOM, Inventory, WorkCenter, Routing

def populate_database():
    db = SessionLocal()

    print("[SEED] Limpando registros antigos em cascata para reconfiguração...")
    db.query(Routing).delete()
    db.query(WorkCenter).delete()
    db.query(BOM).delete()
    db.query(Inventory).delete()
    db.query(Material).delete()
    db.commit()

    print("[SEED] Cadastrando Mestre de Materiais (SAP MARA)...")
    bike = Material(material_code="MAT-FERT-BIKE", description="Bicicleta Mountain Bike Aro 29", material_type="FERT", safety_stock=10, lead_time_days=2)
    roda = Material(material_code="MAT-HALB-RODA", description="Subconjunto Roda Montada Aro 29", material_type="HALB", safety_stock=15, lead_time_days=1)
    pneu = Material(material_code="MAT-ROH-PNEU", description="Pneu de Borracha Aro 29", material_type="ROH", safety_stock=20, lead_time_days=5)
    quadro = Material(material_code="MAT-ROH-QUADRO", description="Quadro de Alumínio", material_type="ROH", safety_stock=5, lead_time_days=7)

    db.add_all([bike, roda, pneu, quadro])
    db.commit()

    print("[SEED] Cadastrando Listas Técnicas (SAP MAST/BOM)...")
    bom1 = BOM(parent_material_id=bike.id, child_material_id=roda.id, qty_required=2)
    bom2 = BOM(parent_material_id=bike.id, child_material_id=quadro.id, qty_required=1)
    bom3 = BOM(parent_material_id=roda.id, child_material_id=pneu.id, qty_required=1)
    db.add_all([bom1, bom2, bom3])

    print("[SEED] Abastecendo o Inventário Inicial divididos por Lote (SAP MARD)...")
    inv_bike = Inventory(material_id=bike.id, batch_number="LOT-BIKE-OLD01", current_stock=5.0)
    inv_roda = Inventory(material_id=roda.id, batch_number="LOT-RODA-A", current_stock=40.0)
    inv_pneu_1 = Inventory(material_id=pneu.id, batch_number="LOT-PNEU-FORN01", current_stock=60.0)
    inv_pneu_2 = Inventory(material_id=pneu.id, batch_number="LOT-PNEU-FORN02", current_stock=40.0)
    inv_quadro = Inventory(material_id=quadro.id, batch_number="LOT-QUADRO-ALUM", current_stock=30.0)
    db.add_all([inv_bike, inv_roda, inv_pneu_1, inv_pneu_2, inv_quadro])

    print("[SEED] Cadastrando Postos de Trabalho / Máquinas (SAP PP-CRP)...")
    linha_montagem = WorkCenter(work_center_code="LINHA-MON-01", description="Linha de Montagem Final de Bicicletas", capacity_hours_per_day=8.0)
    setor_rodas = WorkCenter(work_center_code="SETOR-ROD-02", description="Posto de Centragem e Montagem de Rodas", capacity_hours_per_day=8.0)
    db.add_all([linha_montagem, setor_rodas])
    db.commit()

    print("[SEED] Cadastrando Roteiros de Fabricação e Tempos Padrões (SAP PLPO)...")
    rot_bike = Routing(material_id=bike.id, operation_number=10, work_center_id=linha_montagem.id, setup_time_minutes=5.0, processing_time_minutes=15.0)
    rot_roda = Routing(material_id=roda.id, operation_number=10, work_center_id=setor_rodas.id, setup_time_minutes=2.0, processing_time_minutes=6.0)
    db.add_all([rot_bike, rot_roda])

    db.commit()
    db.close()
    print("[SEED] Banco de dados totalmente restaurado com Capacidades, Roteiros e Lotes!")

if __name__ == "__main__":
    init_db()
    populate_database()