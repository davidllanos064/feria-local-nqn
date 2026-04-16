from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    email = Column(String, unique=True, index=True)
    password_hashed = Column(String)
    tipo = Column(String) # "comprador" o "vendedor"
    whatsapp = Column(String)
    
    # --- SISTEMA DE PLANES Y PAGOS ---
    plan = Column(String, default="Basico") # "Basico" o "Premium"
    esta_bloqueado = Column(Boolean, default=False)
    # PILAR 3: Fecha de vencimiento para automatizar bloqueos
    plan_vencimiento = Column(DateTime, nullable=True)
    
    # Datos de cobro del Vendedor
    vendedor_cbu = Column(String, nullable=True)
    vendedor_alias = Column(String, nullable=True)

    # Relaciones
    productos = relationship("Producto", back_populates="vendedor")
    publicidades = relationship("Publicidad", back_populates="vendedor")

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    descripcion = Column(String)
    precio = Column(Float)
    categoria = Column(String)
    imagenes_urls = Column(String) # URLs separadas por comas
    
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"))
    vendedor = relationship("Usuario", back_populates="productos")

class Publicidad(Base):
    __tablename__ = "publicidades"
    id = Column(Integer, primary_key=True, index=True)
    imagen_url = Column(String)
    estado = Column(String, default="pendiente") # "pendiente", "aprobada", "rechazada"
    
    vendedor_id = Column(Integer, ForeignKey("usuarios.id"))
    vendedor = relationship("Usuario", back_populates="publicidades")