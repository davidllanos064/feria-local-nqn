from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    email = Column(String, unique=True, index=True)
    password_hashed = Column(String)
    tipo = Column(String)
    cbu = Column(String, nullable=True)
    alias = Column(String, nullable=True)
    productos = relationship("Producto", back_populates="vendedor")

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    precio = Column(Float)
    categoria = Column(String)
    descripcion = Column(String)
    imagenes_urls = Column(String)
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"))
    vendedor = relationship("Usuario", back_populates="productos")