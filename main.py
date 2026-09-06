# meu_sistema_pcp/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # ADICIONE ESTA LINHA
from database.connection import init_db
from api.v1.endpoints import router as api_router

app = FastAPI(
    title="Sistema PCP Standalone - Padrão SAP",
    description="API Engine para Planejamento e Controle de Production Industrial",
    version="1.0.0"
)

# --- ADICIONE ESTE BLOCO DE SEGURANÇA CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite que qualquer página HTML local consulte a API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------------------

init_db()

app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    print("\n[SERVIDOR] Iniciando servidor web do PCP...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
