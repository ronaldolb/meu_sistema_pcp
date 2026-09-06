# meu_sistema_pcp/seed.py
from database.connection import SessionLocal, init_db
from database.models import Material, BOM, Inventory

def populate_database():
    db = SessionLocal()
    
    # 1. Limpar dados antigos para não duplicar no teste
    db.query(BOM).delete()
    db.query(Inventory).delete()
    db.query(Material).delete()
    db.commit()  # <--- CERTIFIQUE-SE DE QUE ESTÁ ASSIM (sem a palavra .query)

    print("[SEED] Cadastrando Mestre de Materiais (SAP)...")
    # ... restante do código continua igual

    bike = Material(material_code="MAT-FERT-BIKE", description="Bicicleta Mountain Bike Aro 29", material_type="FERT", safety_stock=10, lead_time_days=2)
    roda = Material(material_code="MAT-HALB-RODA", description="Subconjunto Roda Montada Aro 29", material_type="HALB", safety_stock=15, lead_time_days=1)
    pneu = Material(material_code="MAT-ROH-PNEU", description="Pneu de Borracha Aro 29", material_type="ROH", safety_stock=20, lead_time_days=5)
    quadro = Material(material_code="MAT-ROH-QUADRO", description="Quadro de Alumínio", material_type="ROH", safety_stock=5, lead_time_days=7)
    
    db.add_all([bike, roda, pneu, quadro])
    db.commit() # Salva para gerar os IDs

    print("[SEED] Cadastrando Listas Técnicas (BOM)...")
    # Bike precisa de 2 rodas e 1 quadro
    bom1 = BOM(parent_material_id=bike.id, child_material_id=roda.id, qty_required=2)
    bom2 = BOM(parent_material_id=bike.id, child_material_id=quadro.id, qty_required=1)
    # Roda precisa de 1 pneu
    bom3 = BOM(parent_material_id=roda.id, child_material_id=pneu.id, qty_required=1)
    
    db.add_all([bom1, bom2, bom3])

    print("[SEED] Abastecendo o Inventário Inicial...")
    # Daremos estoque suficiente para a simulação passar!
    inv_bike = Inventory(material_id=bike.id, current_stock=5.0)
    inv_roda = Inventory(material_id=roda.id, current_stock=40.0)    # O suficiente para 15 bikes
    inv_pneu = Inventory(material_id=pneu.id, current_stock=100.0)
    inv_quadro = Inventory(material_id=quadro.id, current_stock=30.0) # O suficiente para 15 bikes
    
    db.add_all([inv_bike, inv_roda, inv_pneu, inv_quadro])
    db.commit()
    db.close()
    print("[SEED] Banco de dados populado com sucesso!")

if __name__ == "__main__":
    init_db() # Garante que as tabelas existem
    populate_database()
