# meu_sistema_pcp/api/v1/endpoints.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from database.connection import get_db
from database.models import Inventory, Material, ProductionOrder
from core.mrp_engine import run_mrp_for_material
from core.shop_floor import release_production_order, confirm_production_order
from core.crp_engine import calculate_work_center_load

router = APIRouter()

# --- MODELOS DE ENTRADA DE DADOS (Validadores do FastAPI) ---
class DemandaComercialInput(BaseModel):
    codigo_material: str
    quantidade: float
    dias_para_entrega: int

class ApontamentoInput(BaseModel):
    codigo_op: str
    quantidade_boa: float
    quantidade_refugo: float


# --- ROTAS HTTP (ENDPOINTS) ---

@router.get("/estoque", summary="Retorna a posição de estoque em tempo real (MARD)")
def listar_estoque(db: Session = Depends(get_db)):
    """ Consulta o inventário real direto do arquivo pcp.db """
    itens = db.query(Inventory).all()
    resultado = []
    for item in itens:
        material = db.query(Material).filter(Material.id == item.material_id).first()
        resultado.append({
            "codigo": material.material_code,
            "descricao": material.description,
            "tipo": material.material_type,
            "estoque_atual": item.current_stock,
            "estoque_seguranca": material.safety_stock
        })
    return resultado


@router.post("/mrp/calcular", summary="Dispara o cálculo de explosão do MRP (MD01)")
def calcular_mrp(dados: DemandaComercialInput, db: Session = Depends(get_db)):
    """ Executa o motor do MRP gerando as ordens e tratando os tipos de dados de forma segura """
    data_entrega = datetime.now() + timedelta(days=dados.dias_para_entrega)
    try:
        ordens_planejadas = run_mrp_for_material(
            db, dados.codigo_material, dados.quantidade, data_entrega
        )
        if not ordens_planejadas:
            return {"status": "sucesso", "mensagem": "Estoque suficiente. Nenhuma OP gerada."}
            
        lista_formatada = []
        for op in ordens_planejadas:
            op_code = getattr(op, 'op_code', 'OP-N/A')
            qty_planned = getattr(op, 'qty_planned', 0.0)
            status = getattr(op, 'status', 'CRTD')
            start_date = getattr(op, 'start_date', '')
            end_date = getattr(op, 'end_date', '')

            lista_formatada.append({
                "op_code": str(op_code),
                "quantidade_planejada": float(qty_planned),
                "status": str(status),
                "data_inicio": str(start_date),
                "data_fim": str(end_date)
            })
            
        return {
            "status": "sucesso",
            "mensagem": f"MRP executado com sucesso! Foram geradas {len(lista_formatada)} Ordens Planejadas.",
            "ordens_geradas": lista_formatada
        }
    except Exception as e:
        db.rollback()
        print(f"\n[ERRO CRÍTICO NO ENDPOINT DO MRP]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno do motor: {str(e)}")


@router.post("/ordens/apontar", summary="Realiza a liberação automática e o apontamento no chão de fábrica (CO11N)")
def apontar_producao(dados: ApontamentoInput, db: Session = Depends(get_db)):
    """ Rota do terminal MES que o operador clica para dar entrada e efetuar o Backflush """
    try:
        liberada = release_production_order(db, dados.codigo_op)
        if not liberada:
            raise HTTPException(
                status_code=400, 
                detail=f"A Ordem {dados.codigo_op} não pôde ser liberada. Verifique se há estoque dos componentes da BOM."
            )
        
        sucesso = confirm_production_order(
            db, dados.codigo_op, dados.quantidade_boa, dados.quantidade_refugo
        )
        
        if sucesso:
            return {"status": "sucesso", "mensagem": f"Ordem {dados.codigo_op} confirmada e estoque atualizado via Backflush!"}
        else:
            raise HTTPException(status_code=500, detail="Falha ao confirmar a ordem de produção.")
            
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        db.rollback()
        print(f"\n[ERRO CRÍTICO NO APONTAMENTO]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno no chão de fábrica: {str(e)}")


@router.get("/capacidade", summary="Retorna o relatório de carga e capacidade das máquinas (CRP)")
def obter_capacidade_maquinas(db: Session = Depends(get_db)):
    """
    Varre as OPs ativas no pcp.db e calcula o percentual de ocupação 
    de cada Posto de Trabalho baseado nos tempos padrões do roteiro.
    """
    try:
        relatorio_carga = calculate_work_center_load(db)
        return relatorio_carga
    except Exception as e:
        print(f"\n[ERRO CRÍTICO NO ENDPOINT CRP]: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao calcular capacidade: {str(e)}")


@router.get("/ordens", summary="Lista todas as Ordens de Produção (fila do PCP - SAP MD04)")
def listar_ordens(db: Session = Depends(get_db)):
    """ Retorna todas as OPs cadastradas no banco, mais recentes primeiro """
    ordens = db.query(ProductionOrder).order_by(ProductionOrder.id.desc()).all()
    resultado = []
    for op in ordens:
        material = db.query(Material).filter(Material.id == op.material_id).first()
        resultado.append({
            "op_code": op.op_code,
            "material": material.material_code if material else "???",
            "qty_planned": float(op.qty_planned or 0.0),
            "qty_confirmed": float(op.qty_confirmed or 0.0),
            "status": op.status,
            "start_date": op.start_date,
            "end_date": op.end_date
        })
    return resultado
