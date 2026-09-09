import sys
import os

# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database.connection import init_db
from api.v1.endpoints import router as api_v1_router

# Inicialização da aplicação FastAPI
app = FastAPI(
    title="Sistema PCP API",
    description="API de Planejamento e Controle de Produção",
    version="1.0.0"
)

# Configuração de CORS para permitir requisições de navegadores/frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Evento de inicialização para criar as tabelas no banco de dados SQLite caso não existam
@app.on_event("startup")
def startup_event():
    init_db()

# Rota raiz de verificação de status do servidor
@app.get("/", tags=["Geral"])
def read_root():
    return {"message": "API do Sistema PCP online e operacional!"}

# Vinculação dos roteadores da API v1 (CRUD de KPIs, Estoque, Ordens de Produção e Lotes)
app.include_router(api_v1_router, prefix="/api/v1")

# Servir arquivos estáticos do front-end (HTML, JS, CSS) se a pasta 'frontend' existir
if os.path.exists("frontend"):
    app.mount("/frontend", StaticFiles(directory="frontend", html=True), name="frontend")