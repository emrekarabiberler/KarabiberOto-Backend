import base64
import os

import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
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

@router.post("/recolor-car")
async def recolor_car(
    file: UploadFile = File(...),
    color_name: str = Form(...),
    color_hex: str = Form(...),
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Only image files are allowed")

    image_bytes = await file.read()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    prompt = (
        "Edit the provided car photo. Keep the same car, background, camera angle, "
        "lighting, reflections, wheels, windows, and details. Change only the car body "
        f"paint color to {color_name} ({color_hex}). Make the result photorealistic, "
        "clean, high quality, and suitable for an automotive paint preview. Return an image."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": file.content_type,
                            "data": image_base64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["Image"],
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {response.text}")

    result = response.json()
    parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text_parts = []

    for part in parts:
        if "text" in part:
            text_parts.append(part["text"])
        inline_data = part.get("inlineData") or part.get("inline_data")
        if inline_data and inline_data.get("data"):
            return {
                "image_base64": inline_data["data"],
                "mime_type": inline_data.get("mimeType") or inline_data.get("mime_type") or "image/png",
                "text": "\n".join(text_parts),
            }

    raise HTTPException(status_code=502, detail="Gemini did not return an image")
