# meu_sistema_pcp/tests/test_api.py
"""
Testes das rotas da API (api/v1/endpoints.py).

Montamos um app FastAPI só com o router e trocamos o get_db pelo banco de teste
(dependency_overrides), assim a API nunca toca o pcp.db real.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.endpoints import router
from database.connection import get_db


@pytest.fixture
def client(db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_mrp_material_inexistente_retorna_404(client):
    resposta = client.get("/mrp/calcular", params={"codigo_material": "NAO-EXISTE", "quantidade": 10})

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Material não encontrado."


def test_mrp_retorna_explosao_em_json(client, bicicleta):
    resposta = client.get("/mrp/calcular", params={"codigo_material": "MAT-FERT-BIKE", "quantidade": 10})

    assert resposta.status_code == 200
    codigos = {linha["material"] for linha in resposta.json()}
    assert codigos == {"MAT-FERT-BIKE", "MAT-HALB-RODA", "MAT-ROH-PNEU", "MAT-ROH-QUADRO"}


def test_mrp_quantidade_invalida_retorna_422(client):
    resposta = client.get("/mrp/calcular", params={"codigo_material": "MAT-FERT-BIKE", "quantidade": "dez"})

    assert resposta.status_code == 422  # o FastAPI valida o tipo antes de chamar o motor


def test_criar_e_listar_material(client):
    novo = {"material_code": "MAT-ROH-ARO", "description": "Aro 29", "material_type": "ROH"}

    criado = client.post("/materiais", json=novo)
    assert criado.status_code == 201
    assert criado.json()["id"] > 0

    lista = client.get("/materiais").json()
    assert [m["material_code"] for m in lista] == ["MAT-ROH-ARO"]


def test_capacidade_retorna_lista_vazia_sem_postos(client):
    resposta = client.get("/capacidade")

    assert resposta.status_code == 200
    assert resposta.json() == []
