import os
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import List, Optional
from datetime import datetime, timedelta
import models
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

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

# --- SISTEMA DE USUARIOS ---

@app.post("/registro")
async def registro(
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    tipo: str = Form(...), # comprador / vendedor
    whatsapp: str = Form(...),
    plan: Optional[str] = Form("Basico"), # Basico / Premium
    db: Session = Depends(get_db)
):
    hashed = pwd_context.hash(password)
    # PILAR 3: Al registrarse, le damos 30 días de vigencia por defecto
    vencimiento = datetime.now() + timedelta(days=30)
    
    nuevo = models.Usuario(
        nombre=nombre, email=email, password_hashed=hashed, 
        tipo=tipo, whatsapp=whatsapp, plan=plan,
        plan_vencimiento=vencimiento, # Asegúrate de tener esta columna en models.py
        esta_bloqueado=False
    )
    db.add(nuevo)
    db.commit()
    return {"status": "ok", "vencimiento": vencimiento}

# --- PRODUCTOS CON LIMITACIÓN DE PLAN (PILAR 1) ---

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
        raise HTTPException(status_code=404, detail="Vendedor no encontrado.")

    # PILAR 3: Control de Vencimiento y Bloqueo
    if vendedor.esta_bloqueado or (vendedor.plan_vencimiento and vendedor.plan_vencimiento < datetime.now()):
        vendedor.esta_bloqueado = True
        db.commit()
        raise HTTPException(status_code=403, detail="Perfil bloqueado o plan vencido. Por favor, regularice su pago.")

    # PILAR 1: Lógica de límites por Plan
    conteo_productos = db.query(models.Producto).filter(models.Producto.vendedor_id == vendedor_id).count()
    
    if vendedor.plan == "Basico":
        if conteo_productos >= 10: 
            raise HTTPException(status_code=400, detail="Límite del Plan Básico alcanzado (10 productos).")
        max_fotos = 3
    elif vendedor.plan == "Premium":
        max_fotos = 10 # Los Premium pueden subir hasta 10 fotos
    else:
        max_fotos = 1 # Por si no tiene plan definido

    # Control estricto de cantidad de fotos enviadas
    if len(imagenes) > max_fotos:
        raise HTTPException(status_code=400, detail=f"Tu plan {vendedor.plan} solo permite {max_fotos} fotos.")

    urls = []
    for img in imagenes:
        res = cloudinary.uploader.upload(await img.read(), folder="feria_nqn")
        urls.append(res["secure_url"])
    
    nuevo = models.Producto(
        nombre=nombre, precio=precio, categoria=categoria,
        descripcion=descripcion, imagenes_urls=",".join(urls), vendedor_id=vendedor_id
    )
    db.add(nuevo)
    db.commit()
    return {"status": "publicado", "fotos_subidas": len(urls)}

# --- WEBHOOK DE MERCADO PAGO (PILAR 2) ---

@app.post("/webhook-pagos")
async def webhook_mercadopago(request: Request, db: Session = Depends(get_db)):
    # Aquí recibimos la notificación de pago
    datos = await request.json()
    
    # En una integración real, aquí consultarías el ID del pago a la API de MP
    # Por ahora simulamos la lógica de actualización:
    if datos.get("type") == "payment":
        payment_id = datos.get("data", {}).get("id")
        # Aquí buscarías quién es el vendedor (puedes usar external_reference de MP)
        # vendedor_id = logic_to_get_vendedor_id_from_mp(payment_id)
        
        # Ejemplo de actualización:
        # u = db.query(models.Usuario).filter(models.Usuario.id == vendedor_id).first()
        # u.plan_vencimiento = datetime.now() + timedelta(days=30)
        # u.esta_bloqueado = False
        # db.commit()
        pass
    
    return {"status": "received"}

# --- PANEL ADMIN (neuquen2026) ---

@app.get("/admin/vendedores")
async def admin_ver_vendedores(clave: str, db: Session = Depends(get_db)):
    if clave != "neuquen2026": raise HTTPException(status_code=401)
    return db.query(models.Usuario).filter(models.Usuario.tipo == "vendedor").all()

@app.post("/admin/actualizar-plan")
async def admin_plan(id: int, clave: str, nuevo_plan: str, db: Session = Depends(get_db)):
    if clave != "neuquen2026": raise HTTPException(status_code=401)
    u = db.query(models.Usuario).filter(models.Usuario.id == id).first()
    u.plan = nuevo_plan
    u.plan_vencimiento = datetime.now() + timedelta(days=30)
    u.esta_bloqueado = False
    db.commit()
    return {"status": "plan actualizado"}

@app.get("/reset-db-viki")
async def reset_db():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    return {"mensaje": "Base de datos reseteada para el sistema de planes y usuarios."}