import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Intentamos leer la variable de Render. Si no existe, usamos la de tu PC local.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Si estamos en Render, a veces hay que ajustar el inicio de la URL
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # Esta es la dirección que usas en tu PC (ajustala si es necesario)
    DATABASE_URL = "postgresql://postgres:1234@127.0.0.1:5432/MarketPlace"

# 2. Creamos el motor de la base de datos
engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-c client_encoding=utf8"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()