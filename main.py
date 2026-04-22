import os, cloudinary, cloudinary.uploader, models
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/productos")
async def get_productos(categoria: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Producto)
    if categoria: query = query.filter(models.Producto.categoria == categoria)
    return query.all()

@app.post("/productos")
async def post_producto(vendedor_id: int = Form(...), nombre: str = Form(...), precio: float = Form(...), 
                        categoria: str = Form(...), imagenes: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    urls = []
    for img in imagenes:
        res = cloudinary.uploader.upload(await img.read(), folder="feria_nqn")
        urls.append(res["secure_url"])
    nuevo = models.Producto(nombre=nombre, precio=precio, categoria=categoria, imagenes_urls=",".join(urls), vendedor_id=vendedor_id)
    db.add(nuevo); db.commit()
    return {"status": "ok"}

@app.get("/vendedor/{vendedor_id}")
async def get_vendedor(vendedor_id: int, db: Session = Depends(get_db)):
    return db.query(models.Usuario).filter(models.Usuario.id == vendedor_id).first()