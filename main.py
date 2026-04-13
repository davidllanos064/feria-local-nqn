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

# --- INICIO: CONFIGURACIÓN PARA RENDER ---
# Esta línea crea las tablas en la base de datos de Render automáticamente
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependencia para obtener la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# --- FIN: CONFIGURACIÓN PARA RENDER ---

# 1. RUTAS ABSOLUTAS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGENES_DIR = os.path.join(BASE_DIR, "imagenes")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Asegurar que la carpeta de imágenes exista
if not os.path.exists(IMAGENES_DIR):
    os.makedirs(IMAGENES_DIR)

# Montar archivos estáticos para las fotos
app.mount("/imagenes", StaticFiles(directory=IMAGENES_DIR), name="imagenes")

# Configurar plantillas
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- RUTAS DE LA APLICACIÓN ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Ruta principal que muestra los productos de la feria"""
    # Buscamos todos los productos en la base de datos de Render
    productos = db.query(models.Producto).all()
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"productos": productos}
    )

@app.post("/productos/", response_model=schemas.Producto)
async def crear_producto(
    nombre: str = Form(...),
    precio: float = Form(...),
    descripcion: str = Form(None),
    imagen: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Ruta para cargar nuevos productos"""
    # Guardamos la imagen en la carpeta local del servidor
    ruta_imagen = os.path.join(IMAGENES_DIR, imagen.filename)
    with open(ruta_imagen, "wb") as buffer:
        shutil.copyfileobj(imagen.file, buffer)
    
    # Creamos el registro en la base de datos
    nuevo_producto = models.Producto(
        nombre=nombre,
        precio=precio,
        descripcion=descripcion,
        imagen_url=f"/imagenes/{imagen.filename}"
    )
    db.add(nuevo_producto)
    db.commit()
    db.refresh(nuevo_producto)
    return nuevo_producto

# Podés seguir agregando tus otras rutas aquí abajo...