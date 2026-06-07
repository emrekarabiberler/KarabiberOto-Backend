from pydantic import BaseModel, Field
from typing import Optional


class CategoryModel(BaseModel):
    id: Optional[str] = Field(default=None, min_length=1)
    name: str
    icon: str = "tag.fill"
    image_url: str = ""

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Pasta Cila",
                "image_url": "https://example.com/category.jpg",
            }
        }
