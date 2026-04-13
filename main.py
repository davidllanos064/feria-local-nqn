import shutil
import os
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

import models
import schemas 
from database import engine, SessionLocal

app = FastAPI()

# 1. RUTAS ABSOLUTAS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGENES_DIR = os.path.join(BASE_DIR, "imagenes")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Asegurar que la carpeta de imágenes exista
if not os.path.exists(IMAGENES_DIR):
    os.makedirs(IMAGENES_DIR)

# 2. CONFIGURACIÓN DE DISEÑO (FRONTEND)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Montamos la carpeta de imágenes para que sean accesibles vía URL
app.mount("/imagenes", StaticFiles(directory=IMAGENES_DIR), name="imagenes")

# 3. MIDDLEWARE PARA CORS (Permite que el frontend se comunique con el backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CREACIÓN DE TABLAS EN LA BASE DE DATOS ---
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- RUTA PRINCIPAL (Lo que ve el cliente al entrar al link) ---

@app.get("/")
async def home(request: Request):
    # Cambiá tu línea 56 por esta:
    return templates.TemplateResponse(
        request=request, name="index.html"
    )

# --- RUTAS DE LA API (Gestión de Productos) ---

@app.post("/productos")
async def crear_producto(
    nombre: str = Form(...),
    descripcion: str = Form(...),
    precio: float = Form(...),
    categoria: str = Form(...), 
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Guardar la imagen físicamente en el servidor
    nombre_seguro = archivo.filename.replace(" ", "_")
    nombre_archivo = f"img_{nombre_seguro}" 
    ruta_fisica = os.path.join(IMAGENES_DIR, nombre_archivo)
    
    with open(ruta_fisica, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
    
    # Guardamos la ruta relativa para que funcione tanto en local como en Render
    url_imagen = f"/imagenes/{nombre_archivo}"
    
    nuevo = models.Producto(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        categoria=categoria, 
        imagen=url_imagen
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@app.get("/productos", response_model=List[schemas.Producto])
def listar_productos(categoria: str = None, busqueda: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Producto)
    
    # Filtros opcionales
    if categoria:
        query = query.filter(models.Producto.categoria == categoria)
    
    if busqueda:
        query = query.filter(models.Producto.nombre.ilike(f"%{busqueda}%"))
        
    return query.all()

@app.delete("/productos/{producto_id}")
def borrar_producto(producto_id: int, db: Session = Depends(get_db)):
    db_producto = db.query(models.Producto).filter(models.Producto.id == producto_id).first()
    if db_producto:
        try:
            # Borrar la imagen del servidor al eliminar el producto
            nombre_fichero = db_producto.imagen.split("/")[-1]
            ruta_fichero = os.path.join(IMAGENES_DIR, nombre_fichero)
            if os.path.exists(ruta_fichero):
                os.remove(ruta_fichero)
        except Exception as e:
            print(f"Error al borrar archivo: {e}")
            
        db.delete(db_producto)
        db.commit()
        return {"mensaje": "Eliminado"}
    
    raise HTTPException(status_code=404, detail="No encontrado")