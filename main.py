import os
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional

import models
from database import engine, SessionLocal

# --- CONFIGURACIÓN DE BASE DE DATOS ---
# Esto asegura que las tablas se creen en Render al iniciar
models.Base.metadata.create_all(bind=engine)

# --- CONFIGURACIÓN DE CLOUDINARY ---
cloudinary.config( 
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.getenv("CLOUDINARY_API_KEY"), 
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

app = FastAPI()

# Configuración de CORS para que el frontend pueda comunicarse sin bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencia para obtener la conexión a la DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Configuración de carpetas de plantillas
templates = Jinja2Templates(directory="templates")

# --- RUTAS ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # CORRECCIÓN CLAVE: En las versiones nuevas se debe pasar el contexto 
    # de esta forma para evitar el error 'unhashable type: dict'.
    return templates.TemplateResponse(
        request=request, name="index.html", context={"request": request}
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
    
    # Formateamos la respuesta para incluir la galería y datos del vendedor
    return [{
        "id": p.id,
        "nombre": p.nombre,
        "precio": p.precio,
        "descripcion": p.descripcion or "Sin descripción",
        "categoria": p.categoria or "General",
        "imagenes": p.imagenes_urls.split(",") if p.imagenes_urls else [],
        "vendedor": {
            "nombre": p.vendedor_nombre,
            "whatsapp": p.vendedor_whatsapp,
            "ubicacion": p.vendedor_ubicacion,
            "cbu": p.vendedor_cbu,
            "alias": p.vendedor_alias,
            "local": p.vendedor_local_nombre
        }
    } for p in productos]

@app.post("/productos")
async def crear_producto(
    nombre: str = Form(...),
    precio: float = Form(...),
    categoria: str = Form(...),
    descripcion: str = Form(None),
    # Campos del Vendedor
    vendedor_nombre: str = Form(...),
    vendedor_whatsapp: str = Form(...),
    vendedor_ubicacion: str = Form(...),
    vendedor_cbu: str = Form(None),
    vendedor_alias: str = Form(None),
    vendedor_local_nombre: str = Form(None),
    # Lista de archivos (Soporta múltiples imágenes)
    imagenes: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    try:
        urls_subidas = []
        # Subimos cada imagen a Cloudinary (limitamos a 5 para optimizar espacio)
        for img in imagenes[:5]:
            # Leer el contenido del archivo
            file_content = await img.read()
            upload_result = cloudinary.uploader.upload(
                file_content, 
                folder="mercado_feria_nqn"
            )
            urls_subidas.append(upload_result["secure_url"])
        
        # Unimos las URLs en un solo string separado por comas
        cadena_imagenes = ",".join(urls_subidas)
        
        nuevo = models.Producto(
            nombre=nombre,
            precio=precio,
            categoria=categoria,
            descripcion=descripcion or "Sin descripción",
            imagenes_urls=cadena_imagenes,
            vendedor_nombre=vendedor_nombre,
            vendedor_whatsapp=vendedor_whatsapp,
            vendedor_ubicacion=vendedor_ubicacion,
            vendedor_cbu=vendedor_cbu,
            vendedor_alias=vendedor_alias,
            vendedor_local_nombre=vendedor_local_nombre
        )
        
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return nuevo
        
    except Exception as e:
        print(f"Error detectado: {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar el producto: {str(e)}")

@app.delete("/productos/{p_id}")
async def eliminar_producto(p_id: int, db: Session = Depends(get_db)):
    producto = db.query(models.Producto).filter(models.Producto.id == p_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(producto)
    db.commit()
    return {"status": "borrado correctamente"}

# --- RUTA DE EMERGENCIA: RESETEAR BASE DE DATOS ---
# Úsala solo una vez visitando: https://feria-local-nqn.onrender.com/reset-db-viki
@app.get("/reset-db-viki")
async def reset_db():
    try:
        # Borra todas las tablas existentes
        models.Base.metadata.drop_all(bind=engine)
        # Crea las tablas de nuevo con la estructura actualizada
        models.Base.metadata.create_all(bind=engine)
        return {"mensaje": "¡Éxito! La base de datos fue reseteada. Ya podés subir productos con fotos y CBU."}
    except Exception as e:
        return {"error": f"No se pudo resetear la base de datos: {str(e)}"}