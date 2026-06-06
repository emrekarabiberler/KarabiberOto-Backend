from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(request: ChatRequest):
    return {"reply": f"AI Asistanı: {request.message} sorunuzu aldım, yakında cevaplayacağım."}

@router.post("/segment-vehicle")
async def segment_vehicle(file: UploadFile = File(...)):
    # This would use rembg or a similar library to process the image
    return {"message": "Image received and mask would be generated here", "filename": file.filename}
