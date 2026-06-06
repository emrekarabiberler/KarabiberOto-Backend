import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from typing import List
from app.database import get_database
from app.models.product import ProductModel
from bson import ObjectId

router = APIRouter()

def serialize_product(product):
    if product and "_id" in product:
        product["_id"] = str(product["_id"])
    return product

@router.get("/", response_model=List[ProductModel])
async def get_products(db = Depends(get_database)):
    products = await db["products"].find().to_list(100)
    return [serialize_product(product) for product in products]

@router.post("/", response_model=ProductModel)
async def create_product(product: ProductModel = Body(...), db = Depends(get_database)):
    product_dict = product.model_dump(by_alias=True, exclude_none=True)

    if "_id" in product_dict:
        if not ObjectId.is_valid(product_dict["_id"]):
            raise HTTPException(status_code=422, detail="Invalid product id")
        product_dict["_id"] = ObjectId(product_dict["_id"])
    
    result = await db["products"].insert_one(product_dict)
    new_product = await db["products"].find_one({"_id": result.inserted_id})
    return serialize_product(new_product)

@router.post("/upload-image")
async def upload_product_image(file: UploadFile = File(...)):
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Cloudinary package is not installed") from exc

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Only image files are allowed")

    if not all([
        os.getenv("CLOUDINARY_CLOUD_NAME"),
        os.getenv("CLOUDINARY_API_KEY"),
        os.getenv("CLOUDINARY_API_SECRET"),
    ]):
        raise HTTPException(status_code=500, detail="Cloudinary credentials are not configured")

    folder = os.getenv("CLOUDINARY_FOLDER", "karabiberoto/products")
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

    try:
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder=folder,
            public_id=f"product-{uuid4()}",
            resource_type="image",
            overwrite=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {exc}") from exc

    return {
        "url": upload_result["secure_url"],
        "public_id": upload_result["public_id"],
    }

@router.get("/barcode/{barcode_id}", response_model=ProductModel)
async def get_product_by_barcode(barcode_id: str, db = Depends(get_database)):
    product = await db["products"].find_one({"barcode": barcode_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)

@router.get("/categories")
async def get_categories():
    # This could also be a separate collection, but for now returning static list
    return [
        {"id": "interior", "name": "İç Cephe"},
        {"id": "exterior", "name": "Dış Cephe"},
        {"id": "primer", "name": "Astarlar"}
    ]
