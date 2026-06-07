from pydantic import BaseModel, Field


class CategoryModel(BaseModel):
    id: str = Field(..., min_length=1)
    name: str
    icon: str = "tag.fill"
    image_url: str = ""

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "polishing",
                "name": "Pasta Cila",
                "icon": "sparkles",
                "image_url": "https://example.com/category.jpg",
            }
        }
