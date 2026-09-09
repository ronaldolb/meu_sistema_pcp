from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Caminho do banco de dados (Cria um arquivo pcp.db na raiz do projeto)
DATABASE_URL = "sqlite:///./pcp.db"

# Engine de conexão com suporte a concorrência para FastAPI
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Fabrica de sessões para requisições no banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa criada AQUI para evitar importação circular com models.py
Base = declarative_base()

def init_db():
    """
    Importa os modelos para registrá-los no SQLAlchemy e cria as tabelas no banco de dados.
    """
    import database.models  # Import local para garantir o registro dos modelos
    Base.metadata.create_all(bind=engine)
    print("[BANCO DE DADOS] Tabelas t_materials, t_bom, t_inventory e t_production_orders criadas/verificadas com sucesso!")

def get_db():
    """
    Gerenciador de contexto (Dependency Injection) para abrir e fechar sessões no FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()