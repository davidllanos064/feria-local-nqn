import shutil
import os
import uuid
import cloudinary
import cloudinary.uploader
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

# --- CONFIGURACIÓN DE CLOUDINARY ---
cloudinary.config( 
  cloud_name = "drqup5lr8", 
  api_key = "121445653389898", 
  api_secret = "PEGA_AQUÍ_TU_API_SECRET", # <--- PEGA AQUÍ EL CÓDIGO QUE COPIASTE
  secure = True
)

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
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ya no necesitamos crear la carpeta 'imagenes' localmente para los nuevos productos
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- RUTAS DE LA APLICACIÓN ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"request": request}
    )

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
        "imagen": p.imagen_url 
    } for p in productos]

# C. Guarda nuevos productos (MODIFICADO PARA CLOUDINARY)
@app.post("/productos")
async def crear_producto(
    nombre: str = Form(...),
    precio: float = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(None),
    imagen: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # 1. Subir la imagen a Cloudinary
        # Usamos el archivo directamente desde la memoria
        upload_result = cloudinary.uploader.upload(
            imagen.file, 
            folder="mercado_feria_nqn"
        )
        
        # 2. Obtener la URL segura que nos da la nube
        url_permanente = upload_result["secure_url"]
        
        # 3. Guardar en la base de datos de Neuquén
        nuevo = models.Producto(
            nombre=nombre,
            precio=precio,
            categoria=categoria,
            descripcion=descripcion or "Sin descripción",
            imagen_url=url_permanente  # <--- URL permanente de internet
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error al subir la foto a la nube")

@app.delete("/productos/{p_id}")
async def eliminar_producto(p_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == p_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(producto)
    db.commit()
    return {"status": "borrado"}