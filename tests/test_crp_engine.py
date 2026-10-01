# meu_sistema_pcp/tests/test_crp_engine.py
"""Testes do cálculo de capacidade / carga de máquina (core/crp_engine.py)."""
from core.crp_engine import calcular_carga_postos


def test_carga_de_uma_ordem_aberta(db, criar_material, criar_posto, criar_roteiro, criar_ordem):
    roda = criar_material("MAT-HALB-RODA", "HALB")
    laser = criar_posto("LASER-17-01", capacidade_horas=10)
    criar_roteiro(roda, laser, setup_min=30, processo_min=3)
    criar_ordem("OP-001", roda, planejado=100)

    [carga] = calcular_carga_postos(db)

    # 30 min de setup + 100 peças x 3 min = 330 min = 5,5 h
    assert carga["required_hours"] == 5.5
    assert carga["load_percentage"] == 55.0


def test_ordem_confirmada_nao_gera_carga(db, criar_material, criar_posto, criar_roteiro, criar_ordem):
    roda = criar_material("MAT-HALB-RODA", "HALB")
    laser = criar_posto("LASER-17-01", capacidade_horas=10)
    criar_roteiro(roda, laser, setup_min=30, processo_min=3)
    criar_ordem("OP-001", roda, planejado=100, confirmado=100, status="CNF")

    [carga] = calcular_carga_postos(db)

    assert carga["required_hours"] == 0
    assert carga["load_percentage"] == 0


def test_apontamento_parcial_considera_so_o_saldo(db, criar_material, criar_posto, criar_roteiro, criar_ordem):
    roda = criar_material("MAT-HALB-RODA", "HALB")
    laser = criar_posto("LASER-17-01", capacidade_horas=10)
    criar_roteiro(roda, laser, setup_min=30, processo_min=3)
    criar_ordem("OP-001", roda, planejado=100, confirmado=40)

    [carga] = calcular_carga_postos(db)

    # saldo de 60 peças: 30 + 60 x 3 = 210 min = 3,5 h
    assert carga["required_hours"] == 3.5
    assert carga["load_percentage"] == 35.0


def test_varias_ordens_somam_no_mesmo_posto(db, criar_material, criar_posto, criar_roteiro, criar_ordem):
    roda = criar_material("MAT-HALB-RODA", "HALB")
    laser = criar_posto("LASER-17-01", capacidade_horas=10)
    criar_roteiro(roda, laser, setup_min=30, processo_min=3)
    criar_ordem("OP-001", roda, planejado=100)  # 5,5 h
    criar_ordem("OP-002", roda, planejado=50)   # 30 + 150 = 180 min = 3 h

    [carga] = calcular_carga_postos(db)

    assert carga["required_hours"] == 8.5
    assert carga["load_percentage"] == 85.0


def test_posto_sem_capacidade_nao_divide_por_zero(db, criar_material, criar_posto, criar_roteiro, criar_ordem):
    roda = criar_material("MAT-HALB-RODA", "HALB")
    parado = criar_posto("DOBRA-06-03", capacidade_horas=0)
    criar_roteiro(roda, parado, setup_min=10, processo_min=1)
    criar_ordem("OP-001", roda, planejado=10)

    [carga] = calcular_carga_postos(db)

    assert carga["load_percentage"] == 0.0


def test_posto_sem_roteiro_aparece_com_carga_zero(db, criar_posto):
    criar_posto("CALANDRA-20-01", capacidade_horas=8)

    [carga] = calcular_carga_postos(db)

    assert carga["work_center_code"] == "CALANDRA-20-01"
    assert carga["required_hours"] == 0
