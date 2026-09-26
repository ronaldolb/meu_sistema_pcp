# meu_sistema_pcp/api/v1/endpoints.py
from api.v1.schemas import (
    MaterialCreate, MaterialUpdate, MaterialResponse, InventoryResponse,
)
from database.models import Material, ProductionOrder, Inventory, BatchGenealogy, BOM, StockMovement, PurchaseRequisition
from api.v1.schemas import (
    MaterialCreate, MaterialResponse, InventoryResponse,
    ProductionOrderCreate, ProductionOrderUpdate, ProductionOrderResponse,
    ApontamentoComLotes, WorkCenterLoadResponse,
    RastreabilidadeResponse, GenealogyComponentResponse,
    TransferenciaLoteRequest, AjusteEstoqueRequest, SucataRequest, StockMovementResponse,
    RequisicaoCreate, EmitirPedidoRequest, ReceberPedidoRequest, RequisicaoResponse,
    KPISummaryResponse
)
from core.inventory_ops import transferir_lote, ajustar_estoque, dar_baixa_sucata
from core.purchasing import criar_requisicao, emitir_pedido, receber_pedido, cancelar_requisicao
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from database.models import Material, ProductionOrder, Inventory, BatchGenealogy, BOM, StockMovement
from api.v1.schemas import (
    MaterialCreate, MaterialResponse, InventoryResponse,
    ProductionOrderCreate, ProductionOrderUpdate, ProductionOrderResponse,
    ApontamentoComLotes, WorkCenterLoadResponse,
    RastreabilidadeResponse, GenealogyComponentResponse,
    TransferenciaLoteRequest, AjusteEstoqueRequest, SucataRequest, StockMovementResponse,
    KPISummaryResponse
)
from core.mrp_engine import processar_calculo_mrp
from core.crp_engine import calcular_carga_postos
from core.shop_floor import release_production_order, confirm_production_order_with_batches
from core.inventory_ops import transferir_lote, ajustar_estoque, dar_baixa_sucata

router = APIRouter()


# --- Rotas de KPIs ---
@router.get("/kpis", response_model=KPISummaryResponse, tags=["Cockpit PCP"])
def obter_kpis(db: Session = Depends(get_db)):
    total_materiais = db.query(Material).count()

    materiais_criticos = 0
    for mat in db.query(Material).all():
        estoque_total = sum(l.current_stock for l in db.query(Inventory).filter(Inventory.material_id == mat.id).all())
        if estoque_total < mat.safety_stock:
            materiais_criticos += 1

    total_ops = db.query(ProductionOrder).count()
    ops_liberadas = db.query(ProductionOrder).filter(ProductionOrder.status == "REL").count()
    taxa_calc = round((ops_liberadas / total_ops) * 100) if total_ops > 0 else 0

    return {
        "total_materiais": total_materiais,
        "materiais_criticos": materiais_criticos,
        "total_ops": total_ops,
        "taxa_liberacao": f"{taxa_calc}%"
    }


# --- Rotas de Materiais ---
@router.get("/materiais", response_model=List[MaterialResponse], tags=["Estoque"])
def listar_materiais(db: Session = Depends(get_db)):
    return db.query(Material).all()


@router.post("/materiais", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED, tags=["Estoque"])
def criar_material(material: MaterialCreate, db: Session = Depends(get_db)):
    novo_mat = Material(**material.model_dump())
    db.add(novo_mat)
    db.commit()
    db.refresh(novo_mat)
    return novo_mat


# --- Rota de Estoque por Lote ---
@router.get("/estoque", response_model=List[InventoryResponse], tags=["Estoque"])
def listar_estoque(db: Session = Depends(get_db)):
    return db.query(Inventory).all()


# --- Rota de Componentes (BOM) de um Material ---
@router.get("/materiais/{material_id}/bom", tags=["Estoque"])
def listar_bom(material_id: int, db: Session = Depends(get_db)):
    itens = db.query(BOM).filter(BOM.parent_material_id == material_id).all()
    resultado = []
    for item in itens:
        comp = db.query(Material).filter(Material.id == item.child_material_id).first()
        resultado.append({
            "material_id": comp.id,
            "material_code": comp.material_code,
            "description": comp.description,
            "qty_required": item.qty_required
        })
    return resultado


# --- Rota de MRP ---
@router.get("/mrp/calcular", tags=["MRP"])
def calcular_mrp(codigo_material: str, quantidade: float, db: Session = Depends(get_db)):
    resultado = processar_calculo_mrp(codigo_material, quantidade, db)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Material não encontrado.")
    return resultado


# --- Rota de Capacidade (CRP) ---
@router.get("/capacidade", response_model=List[WorkCenterLoadResponse], tags=["Capacidade (CRP)"])
def obter_capacidade(db: Session = Depends(get_db)):
    return calcular_carga_postos(db)


# --- Rotas de Ordens de Produção ---
def _enriquecer_ordem(ordem: ProductionOrder, db: Session) -> dict:
    material = db.query(Material).filter(Material.id == ordem.material_id).first()
    return {
        "id": ordem.id,
        "op_code": ordem.op_code,
        "material_id": ordem.material_id,
        "material_code": material.material_code if material else None,
        "qty_planned": ordem.qty_planned,
        "qty_confirmed": ordem.qty_confirmed,
        "product_batch": ordem.product_batch,
        "status": ordem.status,
        "start_date": ordem.start_date,
        "end_date": ordem.end_date,
    }


@router.get("/ordens", response_model=List[ProductionOrderResponse], tags=["Ordens de Produção"])
def listar_ordens(db: Session = Depends(get_db)):
    ordens = db.query(ProductionOrder).all()
    return [_enriquecer_ordem(o, db) for o in ordens]


@router.post("/ordens", response_model=ProductionOrderResponse, status_code=status.HTTP_201_CREATED, tags=["Ordens de Produção"])
def criar_ordem(ordem: ProductionOrderCreate, db: Session = Depends(get_db)):
    nova_op = ProductionOrder(**ordem.model_dump())
    db.add(nova_op)
    db.commit()
    db.refresh(nova_op)
    return _enriquecer_ordem(nova_op, db)


@router.put("/ordens/{op_id}", response_model=ProductionOrderResponse, tags=["Ordens de Produção"])
def atualizar_ordem(op_id: int, ordem_update: ProductionOrderUpdate, db: Session = Depends(get_db)):
    ordem = db.query(ProductionOrder).filter(ProductionOrder.id == op_id).first()
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.")

    update_data = ordem_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(ordem, key, value)

    db.commit()
    db.refresh(ordem)
    return _enriquecer_ordem(ordem, db)


@router.delete("/ordens/{op_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Ordens de Produção"])
def deletar_ordem(op_id: int, db: Session = Depends(get_db)):
    ordem = db.query(ProductionOrder).filter(ProductionOrder.id == op_id).first()
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem não encontrada.")
    db.delete(ordem)
    db.commit()


@router.post("/ordens/{op_code}/liberar", tags=["Ordens de Produção"])
def liberar_ordem(op_code: str, db: Session = Depends(get_db)):
    """Executa o Check ATP e libera a OP (status REL) se houver saldo suficiente nos lotes."""
    sucesso = release_production_order(db, op_code)
    if not sucesso:
        raise HTTPException(status_code=400, detail="Ordem não pôde ser liberada (material insuficiente ou OP inexistente).")
    return {"message": f"Ordem {op_code} liberada com sucesso."}


# --- Rota de Apontamento com Rastreabilidade de Lote ---
@router.post("/ordens/apontar", tags=["Chão de Fábrica"])
def apontar_producao(apontamento: ApontamentoComLotes, db: Session = Depends(get_db)):
    sucesso = confirm_production_order_with_batches(
        db,
        op_code=apontamento.op_code,
        qty_produced_good=apontamento.qty_produced_good,
        qty_scrap=apontamento.qty_scrap,
        components_batches=apontamento.components_batches
    )
    if not sucesso:
        raise HTTPException(status_code=400, detail="Falha no apontamento: verifique status da OP e saldo dos lotes informados.")
    return {"message": f"Apontamento da ordem {apontamento.op_code} registrado com sucesso."}


# --- Rota de Rastreabilidade (Genealogia de Lote) ---
@router.get("/rastreabilidade/{op_code}", response_model=RastreabilidadeResponse, tags=["Rastreabilidade"])
def rastrear_ordem(op_code: str, db: Session = Depends(get_db)):
    ordem = db.query(ProductionOrder).filter(ProductionOrder.op_code == op_code).first()
    if not ordem:
        raise HTTPException(status_code=404, detail="Ordem de produção não encontrada.")

    material_pai = db.query(Material).filter(Material.id == ordem.material_id).first()
    genealogia = db.query(BatchGenealogy).filter(BatchGenealogy.production_order_id == ordem.id).all()

    componentes = []
    for g in genealogia:
        comp_material = db.query(Material).filter(Material.id == g.component_material_id).first()
        componentes.append(GenealogyComponentResponse(
            component_material_code=comp_material.material_code if comp_material else "DESCONHECIDO",
            component_batch=g.component_batch,
            qty_consumed=g.qty_consumed
        ))

    return RastreabilidadeResponse(
        op_code=ordem.op_code,
        parent_material_code=material_pai.material_code if material_pai else "DESCONHECIDO",
        parent_batch=ordem.product_batch or "",
        componentes=componentes
    )


# --- Rotas de Movimentação Manual de Estoque ---
@router.post("/estoque/transferir", tags=["Estoque"])
def transferir_estoque(payload: TransferenciaLoteRequest, db: Session = Depends(get_db)):
    sucesso, mensagem = transferir_lote(
        db, payload.material_id, payload.lote_origem, payload.lote_destino, payload.quantidade, payload.motivo
    )
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return {"message": mensagem}


@router.post("/estoque/ajustar", tags=["Estoque"])
def ajustar_estoque_endpoint(payload: AjusteEstoqueRequest, db: Session = Depends(get_db)):
    sucesso, mensagem = ajustar_estoque(
        db, payload.material_id, payload.batch_number, payload.quantidade_delta, payload.motivo
    )
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return {"message": mensagem}


@router.post("/estoque/sucata", tags=["Estoque"])
def sucata_endpoint(payload: SucataRequest, db: Session = Depends(get_db)):
    sucesso, mensagem = dar_baixa_sucata(
        db, payload.material_id, payload.batch_number, payload.quantidade, payload.motivo
    )
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return {"message": mensagem}


@router.get("/estoque/movimentacoes", response_model=List[StockMovementResponse], tags=["Estoque"])
def listar_movimentacoes(material_id: int = None, db: Session = Depends(get_db)):
    query = db.query(StockMovement)
    if material_id:
        query = query.filter(StockMovement.material_id == material_id)
    movimentos = query.order_by(StockMovement.id.desc()).limit(50).all()

    resultado = []
    for m in movimentos:
        mat = db.query(Material).filter(Material.id == m.material_id).first()
        resultado.append({
            "id": m.id,
            "material_id": m.material_id,
            "material_code": mat.material_code if mat else None,
            "batch_number": m.batch_number,
            "movement_type": m.movement_type,
            "quantity_delta": m.quantity_delta,
            "related_batch": m.related_batch,
            "reason": m.reason,
            "created_at": m.created_at
        })
    return resultado

# --- Rotas de Compras (Requisição → Pedido → Recebimento) ---
def _enriquecer_requisicao(req: PurchaseRequisition, db: Session) -> dict:
    material = db.query(Material).filter(Material.id == req.material_id).first()
    return {
        "id": req.id,
        "material_id": req.material_id,
        "material_code": material.material_code if material else None,
        "quantity": req.quantity,
        "status": req.status,
        "supplier": req.supplier,
        "needed_by_date": req.needed_by_date,
        "notes": req.notes,
        "received_batch": req.received_batch,
        "created_at": req.created_at,
    }


@router.get("/compras/requisicoes", response_model=List[RequisicaoResponse], tags=["Compras"])
def listar_requisicoes(status_filtro: str = None, db: Session = Depends(get_db)):
    query = db.query(PurchaseRequisition)
    if status_filtro:
        query = query.filter(PurchaseRequisition.status == status_filtro)
    requisicoes = query.order_by(PurchaseRequisition.id.desc()).all()
    return [_enriquecer_requisicao(r, db) for r in requisicoes]


@router.post("/compras/requisicoes", response_model=RequisicaoResponse, status_code=status.HTTP_201_CREATED, tags=["Compras"])
def criar_requisicao_endpoint(payload: RequisicaoCreate, db: Session = Depends(get_db)):
    sucesso, mensagem, req = criar_requisicao(db, payload.material_id, payload.quantity, payload.needed_by_date, payload.notes)
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return _enriquecer_requisicao(req, db)


@router.post("/compras/requisicoes/{requisition_id}/emitir-pedido", tags=["Compras"])
def emitir_pedido_endpoint(requisition_id: int, payload: EmitirPedidoRequest, db: Session = Depends(get_db)):
    sucesso, mensagem = emitir_pedido(db, requisition_id, payload.supplier)
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return {"message": mensagem}


@router.post("/compras/requisicoes/{requisition_id}/receber", tags=["Compras"])
def receber_pedido_endpoint(requisition_id: int, payload: ReceberPedidoRequest, db: Session = Depends(get_db)):
    sucesso, mensagem = receber_pedido(db, requisition_id, payload.batch_number, payload.quantity_received)
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return {"message": mensagem}


@router.post("/compras/requisicoes/{requisition_id}/cancelar", tags=["Compras"])
def cancelar_requisicao_endpoint(requisition_id: int, db: Session = Depends(get_db)):
    sucesso, mensagem = cancelar_requisicao(db, requisition_id)
    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)
    return {"message": mensagem}