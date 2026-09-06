# meu_sistema_pcp/database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base

# Caminho do banco de dados (Cria um arquivo pcp.db na raiz do projeto)
# Para mudar para PostgreSQL no futuro, bastará alterar esta string:
DATABASE_URL = "sqlite:///./pcp.db"

# O engine é o motor que gerencia a comunicação com o arquivo .db
# 'check_same_thread=False' é uma exigência específica do SQLite para rodar com APIs
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# O SessionLocal é a fábrica de conexões. Cada operação abrirá uma sessão separada.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """ 
    Função que varre o arquivo models.py e cria fisicamente as tabelas 
    no banco de dados caso elas ainda não existam.
    """
    Base.metadata.create_all(bind=engine)
    print("[BANCO DE DADOS] Tabelas t_materials, t_bom, t_inventory e t_production_orders criadas/verificadas com sucesso!")

def get_db():
    """
    Gerenciador de contexto para abrir e fechar sessões de banco de dados.
    Evita vazamento de memória e travamento de arquivos.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
