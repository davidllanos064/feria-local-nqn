from pydantic import BaseModel
from typing import Optional

class ProductoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio: float
    categoria: str

class Producto(ProductoBase):
    id: int
    imagenes_urls: str 

    class Config:
        from_attributes = True