import shutil
import os
import uuid
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import schemas 
from database import engine, SessionLocal

# --- CONFIGURACIÓN DE BASE DE DATOS ---
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 1. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. RUTAS DE ARCHIVOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGENES_DIR = os.path.join(BASE_DIR, "imagenes")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if not os.path.exists(IMAGENES_DIR):
    os.makedirs(IMAGENES_DIR)

app.mount("/imagenes", StaticFiles(directory=IMAGENES_DIR), name="imagenes")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- RUTAS DE LA APLICACIÓN ---

# A. Carga la página (CORREGIDO PARA EVITAR EL ERROR EN RENDER)
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Esta sintaxis es la única que acepta la versión de FastAPI en Render
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"request": request}
    )
# B. Envía la lista de productos
@app.get("/productos")
async def listar_productos(
    categoria: Optional[str] = None, 
    busqueda: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    query = db.query(models.Producto)
    if categoria:
        query = query.filter(models.Producto.categoria == categoria)
    if busqueda:
        query = query.filter(models.Producto.nombre.ilike(f"%{busqueda}%"))
    
    productos = query.all()
    
    return [{
        "id": p.id,
        "nombre": p.nombre,
        "precio": p.precio,
        "descripcion": p.descripcion or "Sin descripción",
        "categoria": p.categoria or "General",
        "imagen": p.imagen_url # Esto coincide con tu models.py corregido
    } for p in productos]

# C. Guarda nuevos productos
@app.post("/productos")
async def crear_producto(
    nombre: str = Form(...),
    precio: float = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(None),
    imagen: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ext = imagen.filename.split(".")[-1]
    nombre_seguro = f"{uuid.uuid4()}.{ext}"
    ruta_guardado = os.path.join(IMAGENES_DIR, nombre_seguro)
    
    with open(ruta_guardado, "wb") as buffer:
        shutil.copyfileobj(imagen.file, buffer)
    
    nuevo = models.Producto(
        nombre=nombre,
        precio=precio,
        categoria=categoria,
        descripcion=descripcion or "Sin descripción",
        imagen_url=f"/imagenes/{nombre_seguro}"
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# D. Elimina productos
@app.delete("/productos/{p_id}")
async def eliminar_producto(p_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == p_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(producto)
    db.commit()
    return {"status": "borrado"}