# meu_sistema_pcp/api/v1/schemas.py
from pydantic import BaseModel
from typing import Optional, List


# --- Schemas de Materiais ---
class MaterialBase(BaseModel):
    material_code: str
    description: str
    material_type: str  # FERT, HALB, ROH
    safety_stock: float = 0.0
    lead_time_days: int = 1
    backflush: bool = True


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    material_code: Optional[str] = None
    description: Optional[str] = None
    material_type: Optional[str] = None
    safety_stock: Optional[float] = None
    lead_time_days: Optional[int] = None
    backflush: Optional[bool] = None


class MaterialResponse(MaterialBase):
    id: int

    class Config:
        from_attributes = True


# --- Schemas de Estoque (Inventory por Lote) ---
class InventoryResponse(BaseModel):
    id: int
    material_id: int
    batch_number: str
    current_stock: float

    class Config:
        from_attributes = True


# --- Schemas de Componentes (BOM) ---
class BOMComponentResponse(BaseModel):
    material_id: int
    material_code: str
    description: str
    qty_required: float


# --- Schemas de Ordens de Produção ---
class ProductionOrderBase(BaseModel):
    op_code: str
    material_id: int
    qty_planned: float
    qty_confirmed: Optional[float] = 0.0
    product_batch: Optional[str] = None
    status: Optional[str] = "CRTD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ProductionOrderCreate(ProductionOrderBase):
    pass


class ProductionOrderUpdate(BaseModel):
    qty_confirmed: Optional[float] = None
    status: Optional[str] = None
    product_batch: Optional[str] = None


class ProductionOrderResponse(ProductionOrderBase):
    id: int
    material_code: Optional[str] = None

    class Config:
        from_attributes = True


# --- Schema para apontamento com lotes ---
class ApontamentoComLotes(BaseModel):
    op_code: str
    qty_produced_good: float
    qty_scrap: float = 0.0
    components_batches: dict  # {"MAT-ROH-PNEU": "LOT-PNEU-FORN01", ...}


# --- Schemas de Capacidade (CRP) ---
class WorkCenterLoadResponse(BaseModel):
    work_center_code: str
    description: str
    capacity_hours_per_day: float
    required_hours: float
    load_percentage: float


# --- Schemas de Rastreabilidade (Genealogia de Lote) ---
class GenealogyComponentResponse(BaseModel):
    component_material_code: str
    component_batch: str
    qty_consumed: float


class RastreabilidadeResponse(BaseModel):
    op_code: str
    parent_material_code: str
    parent_batch: str
    componentes: List[GenealogyComponentResponse]


# --- Schemas de Movimentação Manual de Estoque ---
class TransferenciaLoteRequest(BaseModel):
    material_id: int
    lote_origem: str
    lote_destino: str
    quantidade: float
    motivo: Optional[str] = None


class AjusteEstoqueRequest(BaseModel):
    material_id: int
    batch_number: str
    quantidade_delta: float  # positivo (entrada) ou negativo (saída)
    motivo: str


class SucataRequest(BaseModel):
    material_id: int
    batch_number: str
    quantidade: float
    motivo: str


class StockMovementResponse(BaseModel):
    id: int
    material_id: int
    material_code: Optional[str] = None
    batch_number: str
    movement_type: str
    quantity_delta: float
    related_batch: Optional[str] = None
    reason: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# --- Schemas de Compras (Requisição → Pedido → Recebimento) ---
class RequisicaoCreate(BaseModel):
    material_id: int
    quantity: float
    needed_by_date: Optional[str] = None
    notes: Optional[str] = None


class EmitirPedidoRequest(BaseModel):
    supplier: str


class ReceberPedidoRequest(BaseModel):
    batch_number: str
    quantity_received: float


class RequisicaoResponse(BaseModel):
    id: int
    material_id: int
    material_code: Optional[str] = None
    quantity: float
    status: str
    supplier: Optional[str] = None
    needed_by_date: Optional[str] = None
    notes: Optional[str] = None
    received_batch: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# --- Schema dos KPIs do Cockpit PCP ---
class KPISummaryResponse(BaseModel):
    total_materiais: int
    materiais_criticos: int
    total_ops: int
    taxa_liberacao: str
