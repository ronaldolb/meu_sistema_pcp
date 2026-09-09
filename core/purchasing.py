# meu_sistema_pcp/core/purchasing.py
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import PurchaseRequisition, Inventory, StockMovement


def criar_requisicao(db: Session, material_id: int, quantity: float, needed_by_date: str = None, notes: str = None):
    """ Cria uma Requisição de Compra (Equivalente ao ME51N do SAP). """
    if quantity <= 0:
        return False, "Quantidade deve ser maior que zero.", None

    req = PurchaseRequisition(
        material_id=material_id,
        quantity=quantity,
        status="ABERTA",
        needed_by_date=needed_by_date,
        notes=notes,
        created_at=datetime.now().isoformat()
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return True, "Requisição de compra criada com sucesso.", req


def emitir_pedido(db: Session, requisition_id: int, supplier: str):
    """ Transforma a Requisição em Pedido de Compra, definindo o fornecedor (Equivalente ao ME21N do SAP). """
    req = db.query(PurchaseRequisition).filter(PurchaseRequisition.id == requisition_id).first()
    if not req:
        return False, "Requisição não encontrada."
    if req.status != "ABERTA":
        return False, f"Requisição precisa estar ABERTA para emitir pedido (status atual: {req.status})."

    req.status = "PEDIDO_EMITIDO"
    req.supplier = supplier
    db.commit()
    return True, "Pedido de compra emitido com sucesso."


def receber_pedido(db: Session, requisition_id: int, batch_number: str, quantity_received: float):
    """ Dá entrada no material recebido, criando/atualizando o lote no estoque (Equivalente ao MIGO Mov. 101 do SAP). """
    req = db.query(PurchaseRequisition).filter(PurchaseRequisition.id == requisition_id).first()
    if not req:
        return False, "Requisição não encontrada."
    if req.status != "PEDIDO_EMITIDO":
        return False, f"Requisição precisa estar com PEDIDO_EMITIDO para receber (status atual: {req.status})."
    if quantity_received <= 0:
        return False, "Quantidade recebida deve ser maior que zero."

    inv = db.query(Inventory).filter(
        Inventory.material_id == req.material_id,
        Inventory.batch_number == batch_number
    ).first()

    if inv:
        inv.current_stock += quantity_received
    else:
        db.add(Inventory(material_id=req.material_id, batch_number=batch_number, current_stock=quantity_received))

    db.add(StockMovement(
        material_id=req.material_id, batch_number=batch_number, movement_type="RECEBIMENTO_COMPRA",
        quantity_delta=quantity_received, reason=f"Recebimento da requisição #{req.id} ({req.supplier or 'sem fornecedor'})",
        created_at=datetime.now().isoformat()
    ))

    req.status = "RECEBIDA"
    req.received_batch = batch_number
    db.commit()
    return True, "Recebimento registrado com sucesso."


def cancelar_requisicao(db: Session, requisition_id: int):
    req = db.query(PurchaseRequisition).filter(PurchaseRequisition.id == requisition_id).first()
    if not req:
        return False, "Requisição não encontrada."
    if req.status == "RECEBIDA":
        return False, "Não é possível cancelar uma requisição já recebida."

    req.status = "CANCELADA"
    db.commit()
    return True, "Requisição cancelada."