# meu_sistema_pcp/limpar_ordens.py
from database.connection import SessionLocal
from database.models import ProductionOrder

def limpar_ordens():
    db = SessionLocal()

    total = db.query(ProductionOrder).count()
    if total == 0:
        print("Nenhuma Ordem de Produção para limpar.")
        db.close()
        return

    print(f"[LIMPEZA] Apagando {total} Ordens de Produção de teste...")
    db.query(ProductionOrder).delete()
    db.commit()
    db.close()
    print("[LIMPEZA] Concluído. Materiais, BOM, Estoque, WorkCenters e Routings foram preservados.")

if __name__ == "__main__":
    limpar_ordens()