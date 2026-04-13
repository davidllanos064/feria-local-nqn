import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Intentamos leer la variable de Render. Si no existe, usamos la de tu PC local.
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuraciones adicionales para el motor (engine)
connect_args = {"options": "-c client_encoding=utf8"}

if DATABASE_URL:
    # Ajuste necesario para SQLAlchemy en Render (Postgres pide postgresql://)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Render requiere SSL para conectar a la base de datos externa
    connect_args["sslmode"] = "require"
else:
    # Esta es la dirección de tu PC local
    DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/MarketPlace"

# 2. Creamos el motor de la base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args
)

# 3. Configuramos la sesión y la base para los modelos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Función útil para obtener la base de datos en tus rutas de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()