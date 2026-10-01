# meu_sistema_pcp/tests/conftest.py
"""
Fixtures compartilhadas pelos testes.

Cada teste recebe um banco SQLite NOVO e EM MEMÓRIA: nada toca o pcp.db real,
e um teste nunca enxerga os dados de outro.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.connection import Base
from database.models import Material, BOM, Inventory, WorkCenter, Routing, ProductionOrder


@pytest.fixture
def db():
    """Sessão de banco limpa para cada teste."""
    engine = create_engine(
        "sqlite://",  # banco em memória
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # mesma conexão para todo o teste (necessário com :memory:)
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# "Fábricas" de dados: funções que criam registros com poucas linhas no teste
# ---------------------------------------------------------------------------

@pytest.fixture
def criar_material(db):
    """
    Cria um material e, opcionalmente, um lote de estoque.

    Uso: criar_material("MAT-ROH-PNEU", "ROH", estoque=50, estoque_seguranca=5)
    """
    def _criar(codigo, tipo, estoque=0.0, estoque_seguranca=0.0, lote="LOT-TESTE-01"):
        mat = Material(
            material_code=codigo,
            description=f"Descrição de {codigo}",
            material_type=tipo,
            safety_stock=estoque_seguranca,
        )
        db.add(mat)
        db.commit()
        db.refresh(mat)
        if estoque:
            adicionar_lote(db, mat, lote, estoque)
        return mat
    return _criar


def adicionar_lote(db, material, lote, quantidade):
    """Adiciona um lote de estoque a um material."""
    db.add(Inventory(material_id=material.id, batch_number=lote, current_stock=quantidade))
    db.commit()


@pytest.fixture
def ligar_bom(db):
    """Cria uma linha de lista técnica: pai precisa de `qtd` unidades do filho."""
    def _ligar(pai, filho, qtd):
        db.add(BOM(parent_material_id=pai.id, child_material_id=filho.id, qty_required=qtd))
        db.commit()
    return _ligar


@pytest.fixture
def bicicleta(criar_material, ligar_bom):
    """
    Estrutura padrão do seed, sem estoque:

        MAT-FERT-BIKE
        ├── 2x MAT-HALB-RODA
        │      └── 1x MAT-ROH-PNEU
        └── 1x MAT-ROH-QUADRO
    """
    bike = criar_material("MAT-FERT-BIKE", "FERT")
    roda = criar_material("MAT-HALB-RODA", "HALB")
    pneu = criar_material("MAT-ROH-PNEU", "ROH")
    quadro = criar_material("MAT-ROH-QUADRO", "ROH")
    ligar_bom(bike, roda, 2)
    ligar_bom(bike, quadro, 1)
    ligar_bom(roda, pneu, 1)
    return {"bike": bike, "roda": roda, "pneu": pneu, "quadro": quadro}


@pytest.fixture
def criar_posto(db):
    """Cria um posto de trabalho (WorkCenter)."""
    def _criar(codigo, capacidade_horas):
        posto = WorkCenter(
            work_center_code=codigo,
            description=f"Posto {codigo}",
            capacity_hours_per_day=capacidade_horas,
        )
        db.add(posto)
        db.commit()
        db.refresh(posto)
        return posto
    return _criar


@pytest.fixture
def criar_roteiro(db):
    """
    Liga um material a um posto, com tempo de setup e tempo por peça (minutos).
    `operacao` é o número da operação no roteiro (como no SAP: 10, 20, 30...).
    """
    def _criar(material, posto, setup_min, processo_min, operacao=10):
        db.add(Routing(
            material_id=material.id,
            operation_number=operacao,
            work_center_id=posto.id,
            setup_time_minutes=setup_min,
            processing_time_minutes=processo_min,
        ))
        db.commit()
    return _criar


@pytest.fixture
def criar_ordem(db):
    """Cria uma ordem de produção."""
    def _criar(op_code, material, planejado, confirmado=0.0, status="REL"):
        op = ProductionOrder(
            op_code=op_code,
            material_id=material.id,
            qty_planned=planejado,
            qty_confirmed=confirmado,
            status=status,
        )
        db.add(op)
        db.commit()
        return op
    return _criar
