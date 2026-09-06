# meu_sistema_pcp/seed_capacity_only.py
from database.connection import SessionLocal, init_db
from database.models import Material, WorkCenter, Routing

def seed_capacity():
    db = SessionLocal()

    # Evita duplicar se já existir algo
    if db.query(WorkCenter).count() > 0:
        print("[AVISO] Já existem WorkCenters cadastrados. Nada foi alterado.")
        db.close()
        return

    bike = db.query(Material).filter(Material.material_code == "MAT-FERT-BIKE").first()
    roda = db.query(Material).filter(Material.material_code == "MAT-HALB-RODA").first()

    if not bike or not roda:
        print("[ERRO] Materiais MAT-FERT-BIKE ou MAT-HALB-RODA não encontrados. Rode o seed.py principal primeiro.")
        db.close()
        return

    print("[SEED-CRP] Cadastrando Postos de Trabalho...")
    linha_montagem = WorkCenter(
        work_center_code="LINHA-MON-01",
        description="Linha de Montagem Final de Bicicletas",
        capacity_hours_per_day=8.0
    )
    setor_rodas = WorkCenter(
        work_center_code="SETOR-ROD-02",
        description="Posto de Centragem e Montagem de Rodas",
        capacity_hours_per_day=8.0
    )
    db.add_all([linha_montagem, setor_rodas])
    db.commit()
    db.refresh(linha_montagem)
    db.refresh(setor_rodas)

    print("[SEED-CRP] Cadastrando Roteiros de Fabricação...")
    rot_bike = Routing(
        material_id=bike.id, operation_number=10, work_center_id=linha_montagem.id,
        setup_time_minutes=5.0, processing_time_minutes=15.0
    )
    rot_roda = Routing(
        material_id=roda.id, operation_number=10, work_center_id=setor_rodas.id,
        setup_time_minutes=2.0, processing_time_minutes=6.0
    )
    db.add_all([rot_bike, rot_roda])
    db.commit()
    db.close()
    print("[SEED-CRP] WorkCenters e Routings gravados com sucesso!")

if __name__ == "__main__":
    init_db()
    seed_capacity()