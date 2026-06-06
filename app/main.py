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

BASE_DIR = Path(__file__).resolve().parents[1]
ADMIN_WEB_DIR = BASE_DIR / "admin-web"

if ADMIN_WEB_DIR.exists():
    app.mount("/admin", StaticFiles(directory=ADMIN_WEB_DIR, html=True), name="admin")

# CORS Middleware for iOS and web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Include Routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/products", tags=["Products & Barcode"])
app.include_router(ai.router, prefix="/ai", tags=["AI Services"])

@app.get("/")
async def root():
    return {"message": "KarabiberOto Backend API is running"}

@app.get("/health")
async def health():
    return {"status": "ok"}
