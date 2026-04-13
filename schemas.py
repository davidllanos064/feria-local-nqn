from pydantic import BaseModel
from typing import Optional

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    categoria: str

class Producto(ProductoBase):
    id: int
    imagen_url: str # <--- Corregido

    class Config:
        from_attributes = True