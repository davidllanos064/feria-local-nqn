import os, cloudinary, cloudinary.uploader, models
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import List, Optional
from datetime import datetime, timedelta
from database import engine, SessionLocal

# Seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
models.Base.metadata.create_all(bind=engine)

cloudinary.config( 
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.getenv("CLOUDINARY_API_KEY"), 
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# --- RUTAS DE NAVEGACIÓN (HTML) ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Carga la página principal"""
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={}
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def ver_dashboard(request: Request):
    """Ruta para ver el panel del vendedor - Corregida para Render"""
    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={}
    )

# --- SISTEMA DE USUARIOS (REGISTRO Y LOGIN) ---

@app.post("/registro")
async def registro(
    nombre: str = Form(...), email: str = Form(...), password: str = Form(...),
    tipo: str = Form(...), whatsapp: str = Form(...), 
    plan: Optional[str] = Form("Basico"), db: Session = Depends(get_db)
):
    hashed = pwd_context.hash(password[:72])
    vencimiento = datetime.now() + timedelta(days=30)
    
    nuevo = models.Usuario(
        nombre=nombre, email=email, password_hashed=hashed, 
        tipo=tipo, whatsapp=whatsapp, plan=plan,
        plan_vencimiento=vencimiento, esta_bloqueado=False
    )
    db.add(nuevo); db.commit()
    return {"status": "ok", "vencimiento": vencimiento}

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.email == email).first()
    if not user or not pwd_context.verify(password[:72], user.password_hashed):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    return {
        "status": "success",
        "usuario": {
            "id": user.id,
            "nombre": user.nombre,
            "plan": user.plan,
            "vencimiento": user.plan_vencimiento,
            "tipo": user.tipo
        }
    }

# --- CONFIGURACIÓN DE COBRO (CBU / ALIAS) ---

@app.post("/vendedor/configurar-pagos")
async def configurar_pagos(
    vendedor_id: int = Form(...), 
    cbu: Optional[str] = Form(None), 
    alias: Optional[str] = Form(None), 
    db: Session = Depends(get_db)
):
    vendedor = db.query(models.Usuario).filter(models.Usuario.id == vendedor_id).first()
    if not vendedor or vendedor.tipo != "vendedor":
        raise HTTPException(404, "Vendedor no encontrado")
    
    vendedor.cbu = cbu
    vendedor.alias = alias
    db.commit()
    return {"status": "datos de cobro actualizados"}

# --- PRODUCTOS (GET y POST) ---

@app.get("/productos")
async def obtener_productos(categoria: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Producto)
    if categoria:
        query = query.filter(models.Producto.categoria == categoria)
    return query.all()

@app.post("/productos")
async def crear_producto(
    vendedor_id: int = Form(...), 
    nombre: str = Form(...), 
    precio: float = Form(...),
    categoria: str = Form(...), 
    descripcion: str = Form(None),
    imagenes: List[UploadFile] = File(...), 
    db: Session = Depends(get_db)
):
    vendedor = db.query(models.Usuario).filter(models.Usuario.id == vendedor_id).first()
    if not vendedor: 
        raise HTTPException(404, "Vendedor no encontrado.")

    # Subida de imágenes con manejo de errores para evitar el 'Error de conexión'
    urls = []
    try:
        for img in imagenes:
            if img.filename:
                content = await img.read()
                upload_result = cloudinary.uploader.upload(content, folder="feria_nqn")
                urls.append(upload_result["secure_url"])
    except Exception as e:
        print(f"Error subiendo a Cloudinary: {e}")
        raise HTTPException(500, "Error al subir las imágenes")

    nuevo_producto = models.Producto(
        nombre=nombre, 
        precio=precio, 
        categoria=categoria,
        descripcion=descripcion, 
        imagenes_urls=",".join(urls), 
        vendedor_id=vendedor_id
    )
    
    db.add(nuevo_producto)
    db.commit()
    return {"status": "ok", "mensaje": "Producto publicado"}

# --- ADMIN Y MANTENIMIENTO ---

@app.get("/admin/vendedores")
async def admin_ver_vendedores(clave: str, db: Session = Depends(get_db)):
    if clave != "neuquen2026": raise HTTPException(401)
    return db.query(models.Usuario).filter(models.Usuario.tipo == "vendedor").all()

@app.get("/reset-db-viki")
async def reset_db():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    return {"mensaje": "Base de datos reseteada correctamente."}