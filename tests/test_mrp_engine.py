# meu_sistema_pcp/tests/test_mrp_engine.py
"""Testes do motor de MRP (core/mrp_engine.py)."""
from core.mrp_engine import processar_calculo_mrp
from tests.conftest import adicionar_lote


def por_material(resultado):
    """Transforma a lista do MRP num dicionário {codigo_material: linha}."""
    return {linha["material"]: linha for linha in resultado}


def test_material_inexistente_retorna_none(db):
    assert processar_calculo_mrp("NAO-EXISTE", 10, db) is None


def test_estoque_suficiente_nao_explode_componentes(db, bicicleta):
    adicionar_lote(db, bicicleta["bike"], "LOT-BIKE-01", 10)

    resultado = processar_calculo_mrp("MAT-FERT-BIKE", 5, db)

    assert len(resultado) == 1
    assert resultado[0]["necessidade_liquida"] == 0
    assert resultado[0]["acao_sugerida"] == "Estoque Suficiente"


def test_explosao_multinivel_sem_estoque(db, bicicleta):
    resultado = por_material(processar_calculo_mrp("MAT-FERT-BIKE", 10, db))

    # Nível 0: produto acabado
    assert resultado["MAT-FERT-BIKE"]["necessidade_liquida"] == 10
    assert resultado["MAT-FERT-BIKE"]["acao_sugerida"] == "Criar OP"

    # Nível 1: 2 rodas por bike (semiacabado -> OP) e 1 quadro (comprado)
    assert resultado["MAT-HALB-RODA"]["nivel"] == 1
    assert resultado["MAT-HALB-RODA"]["necessidade_liquida"] == 20
    assert resultado["MAT-HALB-RODA"]["acao_sugerida"] == "Criar OP"

    assert resultado["MAT-ROH-QUADRO"]["necessidade_liquida"] == 10
    assert resultado["MAT-ROH-QUADRO"]["acao_sugerida"] == "Gerar Solicitacao Compra"

    # Nível 2: 1 pneu por roda
    assert resultado["MAT-ROH-PNEU"]["nivel"] == 2
    assert resultado["MAT-ROH-PNEU"]["necessidade_liquida"] == 20
    assert resultado["MAT-ROH-PNEU"]["acao_sugerida"] == "Gerar Solicitacao Compra"


def test_estoque_de_varios_lotes_e_somado(db, bicicleta):
    adicionar_lote(db, bicicleta["quadro"], "LOT-QUADRO-FORN01", 3)
    adicionar_lote(db, bicicleta["quadro"], "LOT-QUADRO-FORN02", 4)

    resultado = por_material(processar_calculo_mrp("MAT-FERT-BIKE", 10, db))

    assert resultado["MAT-ROH-QUADRO"]["estoque_atual"] == 7
    assert resultado["MAT-ROH-QUADRO"]["necessidade_liquida"] == 3  # 10 - 7


def test_estoque_de_seguranca_entra_na_necessidade(db, criar_material, ligar_bom):
    bike = criar_material("MAT-FERT-BIKE", "FERT")
    quadro = criar_material("MAT-ROH-QUADRO", "ROH", estoque_seguranca=5)
    ligar_bom(bike, quadro, 1)

    resultado = por_material(processar_calculo_mrp("MAT-FERT-BIKE", 10, db))

    assert resultado["MAT-ROH-QUADRO"]["necessidade_liquida"] == 15  # 10 + 5 de segurança


def test_componente_com_estoque_nao_explode_os_filhos(db, bicicleta):
    adicionar_lote(db, bicicleta["roda"], "LOT-RODA-01", 20)

    resultado = por_material(processar_calculo_mrp("MAT-FERT-BIKE", 10, db))

    assert resultado["MAT-HALB-RODA"]["acao_sugerida"] == "Estoque Suficiente"
    assert "MAT-ROH-PNEU" not in resultado  # roda não será produzida, então não precisa de pneu


def test_semiacabado_usado_em_dois_lugares_explode_nos_dois(db, criar_material, ligar_bom):
    """
    O mesmo semiacabado (CUBO) aparece dentro da RODA e do QUADRO.
    Os rolamentos precisam ser calculados para as DUAS ocorrências.

        BIKE ── 1x RODA ── 1x CUBO ── 2x ROLAMENTO
             └─ 1x QUADRO ─ 1x CUBO ── 2x ROLAMENTO
    """
    bike = criar_material("MAT-FERT-BIKE", "FERT")
    roda = criar_material("MAT-HALB-RODA", "HALB")
    quadro = criar_material("MAT-HALB-QUADRO", "HALB")
    cubo = criar_material("MAT-HALB-CUBO", "HALB")
    rolamento = criar_material("MAT-ROH-ROLAMENTO", "ROH")
    ligar_bom(bike, roda, 1)
    ligar_bom(bike, quadro, 1)
    ligar_bom(roda, cubo, 1)
    ligar_bom(quadro, cubo, 1)
    ligar_bom(cubo, rolamento, 2)

    resultado = processar_calculo_mrp("MAT-FERT-BIKE", 10, db)

    linhas_rolamento = [l for l in resultado if l["material"] == "MAT-ROH-ROLAMENTO"]
    assert len(linhas_rolamento) == 2
    assert sum(l["necessidade_liquida"] for l in linhas_rolamento) == 40


def test_bom_circular_nao_trava_o_calculo(db, criar_material, ligar_bom):
    """Cadastro errado A -> B -> A não pode gerar recursão infinita."""
    a = criar_material("MAT-HALB-A", "HALB")
    b = criar_material("MAT-HALB-B", "HALB")
    ligar_bom(a, b, 1)
    ligar_bom(b, a, 1)

    resultado = processar_calculo_mrp("MAT-HALB-A", 5, db)

    codigos = [l["material"] for l in resultado]
    assert codigos == ["MAT-HALB-A", "MAT-HALB-B"]
