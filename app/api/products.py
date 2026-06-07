import os
import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from typing import List
from app.database import get_database
from app.models.category import CategoryModel, CategoryUpdateModel
from app.models.product import ProductModel, ProductUpdateModel
from bson import ObjectId

router = APIRouter()

def serialize_product(product):
    if product and "_id" in product:
        product["_id"] = str(product["_id"])
    return product

def serialize_category(category):
    if category and "_id" in category:
        category.pop("_id", None)
    return category

def slugify(value: str) -> str:
    value = value.strip().lower()
    replacements = {
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ı": "i",
        "ö": "o",
        "ç": "c",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or f"category-{uuid4().hex[:8]}"

async def make_unique_category_id(db, name: str) -> str:
    base_id = slugify(name)
    candidate = base_id
    suffix = 2

    while await db["categories"].find_one({"id": candidate}):
        candidate = f"{base_id}-{suffix}"
        suffix += 1

    return candidate

async def upload_to_cloudinary(file: UploadFile, folder: str, public_id_prefix: str):
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
            public_id=f"{public_id_prefix}-{uuid4()}",
            resource_type="image",
            overwrite=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {exc}") from exc

    return {
        "url": upload_result["secure_url"],
        "public_id": upload_result["public_id"],
    }

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

@router.put("/{product_id}/", response_model=ProductModel, include_in_schema=False)
@router.put("/{product_id}", response_model=ProductModel)
async def update_product(product_id: str, product: ProductUpdateModel = Body(...), db = Depends(get_database)):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=422, detail="Invalid product id")

    result = await db["products"].update_one(
        {"_id": ObjectId(product_id)},
        {"$set": product.model_dump()},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    updated_product = await db["products"].find_one({"_id": ObjectId(product_id)})
    return serialize_product(updated_product)

@router.delete("/{product_id}/", include_in_schema=False)
@router.delete("/{product_id}")
async def delete_product(product_id: str, db = Depends(get_database)):
    if not ObjectId.is_valid(product_id):
        raise HTTPException(status_code=422, detail="Invalid product id")

    result = await db["products"].delete_one({"_id": ObjectId(product_id)})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")

    return {"ok": True}

@router.post("/upload-image")
async def upload_product_image(file: UploadFile = File(...)):
    folder = os.getenv("CLOUDINARY_FOLDER", "karabiberoto/products")
    return await upload_to_cloudinary(file, folder, "product")

@router.get("/barcode/{barcode_id}", response_model=ProductModel)
async def get_product_by_barcode(barcode_id: str, db = Depends(get_database)):
    product = await db["products"].find_one({"barcode": barcode_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)

@router.get("/categories", response_model=List[CategoryModel])
async def get_categories(db = Depends(get_database)):
    categories = await db["categories"].find().to_list(100)
    return [serialize_category(category) for category in categories]

@router.post("/categories/", response_model=CategoryModel, include_in_schema=False)
@router.post("/categories", response_model=CategoryModel)
async def create_category(category: CategoryModel = Body(...), db = Depends(get_database)):
    category_dict = category.model_dump()
    category_dict["id"] = await make_unique_category_id(db, category.name)
    category_dict["icon"] = category_dict.get("icon") or "tag.fill"
    category_dict["_id"] = category_dict["id"]
    await db["categories"].insert_one(category_dict)
    new_category = await db["categories"].find_one({"id": category_dict["id"]})
    return serialize_category(new_category)

@router.post("/categories/upload-image/", include_in_schema=False)
@router.post("/categories/upload-image")
async def upload_category_image(file: UploadFile = File(...)):
    folder = os.getenv("CLOUDINARY_CATEGORY_FOLDER", "karabiberoto/categories")
    return await upload_to_cloudinary(file, folder, "category")

@router.put("/categories/{category_id}/", response_model=CategoryModel, include_in_schema=False)
@router.put("/categories/{category_id}", response_model=CategoryModel)
async def update_category(category_id: str, category: CategoryUpdateModel = Body(...), db = Depends(get_database)):
    update_data = category.model_dump()
    result = await db["categories"].update_one(
        {"id": category_id},
        {"$set": update_data},
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")

    updated_category = await db["categories"].find_one({"id": category_id})
    return serialize_category(updated_category)

@router.delete("/categories/{category_id}/", include_in_schema=False)
@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, db = Depends(get_database)):
    result = await db["categories"].delete_one({"id": category_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")

    await db["products"].update_many(
        {"category_id": category_id},
        {"$set": {"category_id": "", "product_type": ""}},
    )

    return {"ok": True}
