from pydantic import BaseModel, Field
from typing import List, Optional

class ProductModel(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: str
    price: float
    category_id: str
    image_url: str
    grade: str
    color_hex: str
    product_type: str
    barcode: Optional[str] = None
    stock: int = 0
    stock_count: int = 0
    in_stock: bool = True

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Royal Velvet Matte",
                "description": "Interior • 1 Gal",
                "price": 45.0,
                "category_id": "interior",
                "image_url": "https://example.com/image.jpg",
                "grade": "Interior • 1 Gal",
                "color_hex": "#2D4C7B",
                "product_type": "interior",
                "barcode": "123456789",
                "stock": 12,
                "stock_count": 12,
                "in_stock": True
            }
        }


class ProductUpdateModel(BaseModel):
    name: str
    description: str
    price: float
    category_id: str
    image_url: str
    grade: str = ""
    color_hex: str = "#FFFFFF"
    product_type: str
    barcode: Optional[str] = None
    stock: int = 0
    stock_count: int = 0
    in_stock: bool = True


class PurchaseItemModel(BaseModel):
    product_id: str
    quantity: int


class PurchaseModel(BaseModel):
    items: List[PurchaseItemModel]
