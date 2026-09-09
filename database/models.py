from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database.connection import Base

class Material(Base):
    __tablename__ = 't_materials'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=False)
    material_type = Column(String(10), nullable=False)
    safety_stock = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=1)
    backflush = Column(Boolean, default=True)

    inventory = relationship("Inventory", back_populates="material")


class BOM(Base):
    __tablename__ = 't_bom'

    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    child_material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    qty_required = Column(Float, nullable=False)


class Inventory(Base):
    __tablename__ = 't_inventory'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    batch_number = Column(String(50), nullable=False)
    current_stock = Column(Float, default=0.0)

    material = relationship("Material", back_populates="inventory")


class ProductionOrder(Base):
    __tablename__ = 't_production_orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    op_code = Column(String(50), unique=True, nullable=False)
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    qty_planned = Column(Float, nullable=False)
    qty_confirmed = Column(Float, default=0.0)
    product_batch = Column(String(50))
    status = Column(String(10), default="CRTD")
    start_date = Column(String(20))
    end_date = Column(String(20))


class WorkCenter(Base):
    __tablename__ = 't_work_centers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_center_code = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=False)
    capacity_hours_per_day = Column(Float, default=8.0)


class Routing(Base):
    __tablename__ = 't_routing'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    operation_number = Column(Integer, nullable=False)
    work_center_id = Column(Integer, ForeignKey('t_work_centers.id'), nullable=False)
    setup_time_minutes = Column(Float, default=0.0)
    processing_time_minutes = Column(Float, nullable=False)


class BatchGenealogy(Base):
    __tablename__ = 't_batch_genealogy'

    id = Column(Integer, primary_key=True, autoincrement=True)
    production_order_id = Column(Integer, ForeignKey('t_production_orders.id'), nullable=False)
    parent_batch = Column(String(50), nullable=False)
    component_material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    component_batch = Column(String(50), nullable=False)
    qty_consumed = Column(Float, nullable=False)

class StockMovement(Base):
    """ Log de Movimentações Manuais de Estoque (Equivalente ao MIGO/MB51 do SAP) """
    __tablename__ = 't_stock_movements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    batch_number = Column(String(50), nullable=False)
    movement_type = Column(String(20), nullable=False)  # TRANSFERENCIA, AJUSTE, SUCATA
    quantity_delta = Column(Float, nullable=False)  # positivo = entrada, negativo = saída
    related_batch = Column(String(50))  # lote de origem/destino em transferências
    reason = Column(String(255))
    created_at = Column(String(30))    

class PurchaseRequisition(Base):
    """ Requisição/Pedido de Compra (Equivalente a ME51N + ME21N + MIGO do SAP) """
    __tablename__ = 't_purchase_requisitions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    status = Column(String(20), default="ABERTA")  # ABERTA, PEDIDO_EMITIDO, RECEBIDA, CANCELADA
    supplier = Column(String(255))
    needed_by_date = Column(String(30))
    notes = Column(String(255))
    received_batch = Column(String(50))
    created_at = Column(String(30))    