# meu_sistema_pcp/core/inventory_ops.py
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Inventory, StockMovement


def transferir_lote(db: Session, material_id: int, lote_origem: str, lote_destino: str, quantidade: float, motivo: str = None):
    """ Move quantidade de um lote para outro do mesmo material (Equivalente ao Mov. 311 SAP). """
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero."

    if lote_origem == lote_destino:
        return False, "Lote de origem e destino não podem ser iguais."

    inv_origem = db.query(Inventory).filter(
        Inventory.material_id == material_id,
        Inventory.batch_number == lote_origem
    ).first()

    if not inv_origem or inv_origem.current_stock < quantidade:
        return False, f"Saldo insuficiente no lote de origem ({lote_origem})."

    inv_origem.current_stock -= quantidade

    inv_destino = db.query(Inventory).filter(
        Inventory.material_id == material_id,
        Inventory.batch_number == lote_destino
    ).first()

    if inv_destino:
        inv_destino.current_stock += quantidade
    else:
        db.add(Inventory(material_id=material_id, batch_number=lote_destino, current_stock=quantidade))

    agora = datetime.now().isoformat()
    db.add(StockMovement(material_id=material_id, batch_number=lote_origem, movement_type="TRANSFERENCIA",
                          quantity_delta=-quantidade, related_batch=lote_destino, reason=motivo, created_at=agora))
    db.add(StockMovement(material_id=material_id, batch_number=lote_destino, movement_type="TRANSFERENCIA",
                          quantity_delta=quantidade, related_batch=lote_origem, reason=motivo, created_at=agora))

    db.commit()
    return True, "Transferência realizada com sucesso."


def ajustar_estoque(db: Session, material_id: int, batch_number: str, quantidade_delta: float, motivo: str):
    """ Corrige o saldo de um lote para mais ou para menos, com motivo obrigatório. """
    inv = db.query(Inventory).filter(
        Inventory.material_id == material_id,
        Inventory.batch_number == batch_number
    ).first()

    saldo_atual = inv.current_stock if inv else 0.0
    novo_saldo = saldo_atual + quantidade_delta

    if novo_saldo < 0:
        return False, f"Ajuste resultaria em saldo negativo (atual: {saldo_atual}, ajuste: {quantidade_delta})."

    if inv:
        inv.current_stock = novo_saldo
    else:
        db.add(Inventory(material_id=material_id, batch_number=batch_number, current_stock=novo_saldo))

    db.add(StockMovement(material_id=material_id, batch_number=batch_number, movement_type="AJUSTE",
                          quantity_delta=quantidade_delta, reason=motivo, created_at=datetime.now().isoformat()))

    db.commit()
    return True, "Ajuste de estoque registrado com sucesso."


def dar_baixa_sucata(db: Session, material_id: int, batch_number: str, quantidade: float, motivo: str):
    """ Reduz o saldo de um lote por perda/sucata (Equivalente ao Mov. 551 SAP). """
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero."

    inv = db.query(Inventory).filter(
        Inventory.material_id == material_id,
        Inventory.batch_number == batch_number
    ).first()

    if not inv or inv.current_stock < quantidade:
        return False, "Saldo insuficiente no lote para dar baixa por sucata."

    inv.current_stock -= quantidade

    db.add(StockMovement(material_id=material_id, batch_number=batch_number, movement_type="SUCATA",
                          quantity_delta=-quantidade, reason=motivo, created_at=datetime.now().isoformat()))

    db.commit()
    return True, "Baixa por sucata registrada com sucesso."