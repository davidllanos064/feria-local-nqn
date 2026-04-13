from sqlalchemy import Column, Integer, String, Float
from database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    descripcion = Column(String)
    precio = Column(Float)
    categoria = Column(String)
    # Cambiamos 'imagen' por 'imagen_url' para que coincida con main.py y schemas.py
    imagen_url = Column(String)