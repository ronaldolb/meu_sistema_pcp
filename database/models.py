# meu_sistema_pcp/database/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Material(Base):
    """ Mestre de Materiais (Equivalente às tabelas MARA/MARC do SAP) """
    __tablename__ = 't_materials'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(50), unique=True, nullable=False) # Ex: MAT-FERT-BIKE
    description = Column(String(255), nullable=False)
    material_type = Column(String(10), nullable=False) # FERT, HALB, ROH
    safety_stock = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=1)
    backflush = Column(Boolean, default=True)

    # Relacionamento para enxergar o estoque atual deste material
    inventory = relationship("Inventory", uselist=False, back_populates="material")


class BOM(Base):
    """ Lista Técnica / Estrutura do Produto (Equivalente à tabela MAST/STPO do SAP) """
    __tablename__ = 't_bom'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    parent_material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False) # Produto Pai
    child_material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)  # Componente Filho
    qty_required = Column(Float, nullable=False) # Quantidade necessária do filho para fazer 1 unidade do pai


class Inventory(Base):
    """ Saldo de Estoque Atual (Equivalente à tabela MARD do SAP) """
    __tablename__ = 't_inventory'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_materials.id'), unique=True, nullable=False)
    current_stock = Column(Float, default=0.0) # Estoque físico disponível

    material = relationship("Material", back_populates="inventory")


class ProductionOrder(Base):
    """ Ordens de Produção (Equivalente à tabela AFKO/AFPO do SAP) """
    __tablename__ = 't_production_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    op_code = Column(String(50), unique=True, nullable=False) # Código único da OP
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    qty_planned = Column(Float, nullable=False)
    qty_confirmed = Column(Float, default=0.0)
    status = Column(String(10), default="CRTD") # CRTD, REL, CNF
    start_date = Column(String(20))
    end_date = Column(String(20))


class WorkCenter(Base):
    """ Postos de Trabalho / Máquinas (Equivalente à tabela CRHD do SAP) """
    __tablename__ = 't_work_centers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    work_center_code = Column(String(50), unique=True, nullable=False) # Ex: LINHA-MON-01
    description = Column(String(255), nullable=False)
    capacity_hours_per_day = Column(Float, default=8.0) # Jornada diária disponível da máquina


class Routing(Base):
    """ Roteiro de Fabricação / Operações (Equivalente à tabela PLPO do SAP) """
    __tablename__ = 't_routing'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('t_materials.id'), nullable=False)
    operation_number = Column(Integer, nullable=False) # Sequência: 10, 20, 30
    work_center_id = Column(Integer, ForeignKey('t_work_centers.id'), nullable=False)
    setup_time_minutes = Column(Float, default=0.0) # Tempo de preparação da máquina
    processing_time_minutes = Column(Float, nullable=False) # Tempo por unidade fabricada
