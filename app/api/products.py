from fastapi import APIRouter, Depends, HTTPException, Body
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
