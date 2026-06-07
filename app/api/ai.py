import base64
import io
import os
from typing import Optional

import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image, ImageEnhance, ImageFilter
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
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=422, detail="Only image files are allowed")

    image_bytes = await file.read()
    provider = os.getenv("AI_IMAGE_PROVIDER", "local").lower()
    if provider == "openai":
        return await recolor_with_openai(image_bytes, file.filename, file.content_type, color_name, color_hex)
    if provider == "gemini":
        return await recolor_with_gemini(image_bytes, file.content_type, color_name, color_hex)
    if provider == "pollinations":
        return await recolor_with_pollinations(image_bytes, file.filename, file.content_type, color_name, color_hex)

    return recolor_locally(image_bytes, color_name, color_hex)


async def recolor_with_openai(
    image_bytes: bytes,
    file_name: Optional[str],
    content_type: str,
    color_name: str,
    color_hex: str,
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1-mini")
    prompt = (
        "Edit this car photo. Keep the same vehicle, background, camera angle, lighting, "
        "wheels, windows, shadows, reflections, and all details. Change only the car body "
        f"paint color to {color_name} ({color_hex}). Make the output photorealistic and "
        "suitable for an automotive paint preview."
    )

    files = {
        "image": (file_name or "vehicle.png", image_bytes, content_type),
    }
    data = {
        "model": model,
        "prompt": prompt,
        "size": os.getenv("OPENAI_IMAGE_SIZE", "1024x1024"),
        "quality": os.getenv("OPENAI_IMAGE_QUALITY", "low"),
    }

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            "https://api.openai.com/v1/images/edits",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data,
        )

    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {response.text}")

    result = response.json()
    generated = (result.get("data") or [{}])[0]
    b64_json = generated.get("b64_json")
    if b64_json:
        return {
            "image_base64": b64_json,
            "mime_type": "image/png",
            "text": "OpenAI image edit completed",
        }

    image_url = generated.get("url")
    if image_url:
        async with httpx.AsyncClient(timeout=60) as client:
            image_response = await client.get(image_url)
        if image_response.status_code >= 400:
            raise HTTPException(status_code=502, detail="OpenAI returned an image URL that could not be downloaded")
        return {
            "image_base64": base64.b64encode(image_response.content).decode("utf-8"),
            "mime_type": image_response.headers.get("content-type", "image/png"),
            "text": "OpenAI image edit completed",
        }

    raise HTTPException(status_code=502, detail="OpenAI did not return an image")


def recolor_locally(image_bytes: bytes, color_name: str, color_hex: str):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Image could not be opened") from exc

    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    rgb = image.convert("RGB")
    grayscale = rgb.convert("L")
    color = Image.new("RGB", rgb.size, color_hex)

    tinted = Image.blend(
        Image.merge("RGB", (grayscale, grayscale, grayscale)),
        color,
        0.58,
    )
    tinted = ImageEnhance.Contrast(tinted).enhance(1.08)
    tinted = ImageEnhance.Sharpness(tinted).enhance(1.05)

    mask = build_vehicle_like_mask(rgb)
    result = Image.composite(tinted, rgb, mask).convert("RGBA")
    result.putalpha(image.getchannel("A"))

    buffer = io.BytesIO()
    result.save(buffer, format="PNG", optimize=True)

    return {
        "image_base64": base64.b64encode(buffer.getvalue()).decode("utf-8"),
        "mime_type": "image/png",
        "text": f"Yerel ücretsiz renk önizleme tamamlandı: {color_name}",
    }


def build_vehicle_like_mask(image: Image.Image) -> Image.Image:
    width, height = image.size
    source = image.convert("RGB")
    pixels = source.load()
    mask = Image.new("L", source.size, 0)
    mask_pixels = mask.load()

    for y in range(height):
        vertical_focus = 0.20 <= y / height <= 0.86
        if not vertical_focus:
            continue

        for x in range(width):
            horizontal_focus = 0.05 <= x / width <= 0.95
            if not horizontal_focus:
                continue

            r, g, b = pixels[x, y]
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            brightness = (r + g + b) / 3
            saturation = 0 if max_c == 0 else (max_c - min_c) / max_c

            is_body_like = (
                35 < brightness < 245
                and saturation < 0.42
                and not (r > 210 and g > 210 and b > 210)
            )
            if is_body_like:
                mask_pixels[x, y] = 185

    return mask.filter(ImageFilter.GaussianBlur(radius=max(2, min(width, height) // 160)))


async def recolor_with_pollinations(
    image_bytes: bytes,
    file_name: Optional[str],
    content_type: str,
    color_name: str,
    color_hex: str,
):
    api_key = os.getenv("POLLINATIONS_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="POLLINATIONS_API_KEY is not configured")

    model = os.getenv("POLLINATIONS_IMAGE_MODEL", "kontext")
    prompt = (
        "Edit this car photo. Keep the exact same vehicle, background, camera angle, "
        "lighting, wheels, windows, reflections, and all details. Change only the car "
        f"body paint color to {color_name} ({color_hex}). Make it photorealistic and "
        "suitable for an automotive paint preview."
    )

    files = {
        "image": (file_name or "vehicle.jpg", image_bytes, content_type),
    }
    data = {
        "prompt": prompt,
        "model": model,
        "size": os.getenv("POLLINATIONS_IMAGE_SIZE", "1024x1024"),
        "response_format": "b64_json",
    }

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(
            "https://gen.pollinations.ai/v1/images/edits",
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data,
        )

        if response.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Pollinations request failed: {response.text}")

        result = response.json()
        generated = (result.get("data") or [{}])[0]
        b64_json = generated.get("b64_json")
        if b64_json:
            return {
                "image_base64": b64_json,
                "mime_type": "image/png",
                "text": "Pollinations image edit completed",
            }

        image_url = generated.get("url")
        if image_url:
            image_response = await client.get(image_url)
            if image_response.status_code >= 400:
                raise HTTPException(status_code=502, detail="Pollinations returned an image URL that could not be downloaded")
            return {
                "image_base64": base64.b64encode(image_response.content).decode("utf-8"),
                "mime_type": image_response.headers.get("content-type", "image/png"),
                "text": "Pollinations image edit completed",
            }

    raise HTTPException(status_code=502, detail="Pollinations did not return an image")


async def recolor_with_gemini(
    image_bytes: bytes,
    content_type: str,
    color_name: str,
    color_hex: str,
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

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
                            "mime_type": content_type,
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
