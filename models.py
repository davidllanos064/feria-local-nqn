from sqlalchemy import Column, Integer, String, Float
from database import Base

class Producto(Base):
    __tablename__ = "productos"

    # --- DATOS DEL PRODUCTO ---
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    descripcion = Column(String)
    precio = Column(Float)
    categoria = Column(String)
    
    # Aquí guardaremos las 5 URLs de Cloudinary separadas por comas
    imagenes_urls = Column(String) 

    # --- DATOS DEL VENDEDOR (NUEVO) ---
    vendedor_nombre = Column(String)
    vendedor_whatsapp = Column(String)
    vendedor_ubicacion = Column(String)
    
    # Datos para el sistema de depósito/transferencia
    vendedor_cbu = Column(String, nullable=True)
    vendedor_alias = Column(String, nullable=True)
    vendedor_local_nombre = Column(String, nullable=True) # Nombre del local o puesto