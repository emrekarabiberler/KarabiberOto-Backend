from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated
from bson import ObjectId

# Custom type for handling MongoDB ObjectId in Pydantic v2
def validate_object_id(v: any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")

PyObjectId = Annotated[str, BeforeValidator(validate_object_id)]

class ProductModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    description: str
    price: float
    category_id: str
    image_url: str
    grade: str
    color_hex: str
    product_type: str
    barcode: Optional[str] = None
    in_stock: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
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
                "in_stock": True
            }
        }
