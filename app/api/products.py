from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from app.database import get_database
from app.models.product import ProductModel
from bson import ObjectId

router = APIRouter()

@router.get("/", response_model=List[ProductModel])
async def get_products(db = Depends(get_database)):
    products = await db["products"].find().to_list(100)
    return products

@router.post("/", response_model=ProductModel)
async def create_product(product: ProductModel = Body(...), db = Depends(get_database)):
    # Convert Pydantic model to dict for MongoDB
    product_dict = product.dict(by_alias=True)
    # If the id is a placeholder or not provided, MongoDB will handle it or we use the generated one
    if "_id" in product_dict and isinstance(product_dict["_id"], str):
        product_dict["_id"] = ObjectId(product_dict["_id"])
    
    result = await db["products"].insert_one(product_dict)
    new_product = await db["products"].find_one({"_id": result.inserted_id})
    return new_product

@router.get("/barcode/{barcode_id}", response_model=ProductModel)
async def get_product_by_barcode(barcode_id: str, db = Depends(get_database)):
    product = await db["products"].find_one({"barcode": barcode_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/categories")
async def get_categories():
    # This could also be a separate collection, but for now returning static list
    return [
        {"id": "interior", "name": "İç Cephe"},
        {"id": "exterior", "name": "Dış Cephe"},
        {"id": "primer", "name": "Astarlar"}
    ]
