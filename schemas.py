from pydantic import BaseModel
from typing import Optional

# Lo que el usuario envía al crear
class ProductoBase(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    categoria: str

# Lo que la API devuelve (incluye datos generados por la DB)
class Producto(ProductoBase):
    id: int
    imagen: str

    class Config:
        from_attributes = True