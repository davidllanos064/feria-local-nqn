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

# Seguridad - Ajustado para evitar errores de versión en Render
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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- SISTEMA DE USUARIOS ---

@app.post("/registro")
async def registro(
    nombre: str = Form(...), email: str = Form(...), password: str = Form(...),
    tipo: str = Form(...), whatsapp: str = Form(...), 
    plan: Optional[str] = Form("Basico"), db: Session = Depends(get_db)
):
    # Truncamos a 72 chars por limitación de bcrypt para evitar el Error 500
    hashed = pwd_context.hash(password[:72])
    vencimiento = datetime.now() + timedelta(days=30)
    
    nuevo = models.Usuario(
        nombre=nombre, email=email, password_hashed=hashed, 
        tipo=tipo, whatsapp=whatsapp, plan=plan,
        plan_vencimiento=vencimiento, esta_bloqueado=False
    )
    db.add(nuevo); db.commit()
    return {"status": "ok", "vencimiento": vencimiento}

# --- PRODUCTOS (GET y POST) ---

@app.get("/productos")
async def obtener_productos(categoria: Optional[str] = None, db: Session = Depends(get_db)):
    """Soluciona el Error 405: Ahora permite ver productos con GET"""
    query = db.query(models.Producto)
    if categoria:
        query = query.filter(models.Producto.categoria == categoria)
    return query.all()

@app.post("/productos")
async def crear_producto(
    vendedor_id: int = Form(...), nombre: str = Form(...), precio: float = Form(...),
    categoria: str = Form(...), descripcion: str = Form(None),
    imagenes: List[UploadFile] = File(...), db: Session = Depends(get_db)
):
    vendedor = db.query(models.Usuario).get(vendedor_id)
    if not vendedor: raise HTTPException(404, "Vendedor no encontrado.")

    # Control de Vencimiento/Bloqueo
    if vendedor.esta_bloqueado or (vendedor.plan_vencimiento and vendedor.plan_vencimiento < datetime.now()):
        vendedor.esta_bloqueado = True; db.commit()
        raise HTTPException(403, "Perfil bloqueado o plan vencido.")

    # Límites de Plan
    conteo = db.query(models.Producto).filter(models.Producto.vendedor_id == vendedor_id).count()
    limits = {"Basico": (10, 3), "Premium": (float('inf'), 10)} # (max_prod, max_fotos)
    max_p, max_f = limits.get(vendedor.plan, (1, 1))

    if conteo >= max_p: raise HTTPException(400, f"Límite de productos alcanzado para plan {vendedor.plan}")
    if len(imagenes) > max_f: raise HTTPException(400, f"Tu plan permite máximo {max_f} fotos.")

    urls = []
    for img in imagenes:
        res = cloudinary.uploader.upload(await img.read(), folder="feria_nqn")
        urls.append(res["secure_url"])
    
    nuevo = models.Producto(
        nombre=nombre, precio=precio, categoria=categoria,
        descripcion=descripcion, imagenes_urls=",".join(urls), vendedor_id=vendedor_id
    )
    db.add(nuevo); db.commit()
    return {"status": "publicado", "fotos_subidas": len(urls)}

# --- MERCADO PAGO Y ADMIN ---

@app.post("/webhook-pagos")
async def webhook_mercadopago(request: Request, db: Session = Depends(get_db)):
    datos = await request.json()
    # Lógica de notificación aquí
    return {"status": "received"}

@app.get("/admin/vendedores")
async def admin_ver_vendedores(clave: str, db: Session = Depends(get_db)):
    if clave != "neuquen2026": raise HTTPException(401)
    return db.query(models.Usuario).filter(models.Usuario.tipo == "vendedor").all()

@app.post("/admin/actualizar-plan")
async def admin_plan(id: int, clave: str, nuevo_plan: str, db: Session = Depends(get_db)):
    if clave != "neuquen2026": raise HTTPException(401)
    u = db.query(models.Usuario).get(id)
    u.plan, u.esta_bloqueado = nuevo_plan, False
    u.plan_vencimiento = datetime.now() + timedelta(days=30)
    db.commit()
    return {"status": "plan actualizado"}

@app.get("/reset-db-viki")
async def reset_db():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    return {"mensaje": "Base de datos reseteada."}