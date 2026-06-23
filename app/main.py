from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import products, ai, auth

app = FastAPI(
    title="KarabiberOto API",
    description="Backend for KarabiberOto iOS Application",
    version="1.0.0"
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
ADMIN_WEB_DIRS = [BACKEND_DIR / "admin-web", ROOT_DIR / "admin-web"]
CUSTOMER_WEB_DIR = ROOT_DIR / "web"

for admin_web_dir in ADMIN_WEB_DIRS:
    if admin_web_dir.exists():
        app.mount("/admin", StaticFiles(directory=admin_web_dir, html=True), name="admin")
        break

if CUSTOMER_WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=CUSTOMER_WEB_DIR, html=True), name="web")

# iOS ve web erişimi için CORS ara katmanı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Routerları ekle
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/products", tags=["Products & Barcode"])
app.include_router(ai.router, prefix="/ai", tags=["AI Services"])

@app.get("/")
async def root():
    return {"message": "KarabiberOto Backend API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}
