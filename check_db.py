# meu_sistema_pcp/check_db.py
from database.connection import SessionLocal
from database.models import Material, ProductionOrder, WorkCenter, Routing

db = SessionLocal()

print("\n=== ORDENS DE PRODUÇÃO (todas, com status) ===")
ops = db.query(ProductionOrder).all()
if not ops:
    print("Nenhuma ordem de produção existe no banco.")
for op in ops:
    mat = db.query(Material).filter(Material.id == op.material_id).first()
    print(f"{op.op_code} | material={mat.material_code if mat else '???'} | qty={op.qty_planned} | status={op.status}")

print("\n=== POSTOS DE TRABALHO (WorkCenter) ===")
wcs = db.query(WorkCenter).all()
if not wcs:
    print("Nenhum WorkCenter cadastrado! (o painel de capacidade sempre virá vazio)")
for wc in wcs:
    print(f"{wc.work_center_code} | {wc.description} | {wc.capacity_hours_per_day}h/dia")

print("\n=== ROTEIROS (Routing) ===")
rots = db.query(Routing).all()
if not rots:
    print("Nenhum Routing cadastrado! (sem roteiro, nenhuma OP vira carga de máquina)")
for r in rots:
    mat = db.query(Material).filter(Material.id == r.material_id).first()
    wc = db.query(WorkCenter).filter(WorkCenter.id == r.work_center_id).first()
    print(f"material={mat.material_code if mat else '???'} | work_center={wc.work_center_code if wc else '???'} | setup={r.setup_time_minutes}min | proc={r.processing_time_minutes}min/un")

db.close()