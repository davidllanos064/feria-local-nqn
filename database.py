import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Leemos la variable de entorno de Render.
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuraciones base para el motor
connect_args = {"options": "-c client_encoding=utf8"}

if DATABASE_URL:
    # Ajuste para SQLAlchemy: Render usa postgres:// pero SQLAlchemy requiere postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Render requiere SSL para conectar a bases de datos gestionadas (como Neon o Render DB)
    # Importante: Algunos drivers prefieren pasarlo en la URL, otros en connect_args
    connect_args["sslmode"] = "require"
else:
    # Dirección local para desarrollo en tu PC
    DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/MarketPlace"

# 2. Creamos el motor de la base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # PILAR TÉCNICO: pool_pre_ping verifica que la conexión esté viva antes de usarla.
    # Esto soluciona la mayoría de los errores de "No open ports detected" en Render.
    pool_pre_ping=True,
    # Ayuda a liberar conexiones inactivas
    pool_recycle=300 
)

# 3. Configuramos la sesión y la base para los modelos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Función para obtener la base de datos en tus rutas de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()