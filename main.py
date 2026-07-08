import os
import sys
import base64
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure the current directory is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

import stone_bw_variations

app = FastAPI(title="Stone Inscription Preprocessor Server (Stateless)")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(CURRENT_DIR, "static")

def to_base64_data_url(img, format_name=".png"):
    """Helper to convert OpenCV image to base64 Data URL."""
    _, buffer = cv2.imencode(format_name, img)
    b64_str = base64.b64encode(buffer).decode("utf-8")
    mime_type = "image/png" if format_name == ".png" else "image/jpeg"
    return f"data:{mime_type};base64,{b64_str}"

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')):
        raise HTTPException(status_code=400, detail="Invalid image file format.")
    
    try:
        # Read file bytes in memory
        raw_bytes = await file.read()
        
        # Convert bytes to OpenCV image
        nparr = np.frombuffer(raw_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Failed to decode image.")
            
        # Convert raw uploaded image to base64
        # Guess mime type based on extension
        ext = os.path.splitext(file.filename)[1].lower()
        raw_format = ".png" if ext == ".png" else ".jpg"
        raw_base64 = to_base64_data_url(img, raw_format)
        
        # Convert to gray
        # Port load_gray logic to in-memory image
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        max_width = 1800
        upscale = 1.5
        if w * upscale > max_width:
            upscale = max_width / w
        if upscale != 1.0:
            gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
        
        # Define variations
        variations = [
            ("01_otsu_global", stone_bw_variations.otsu_global(gray)),
            ("02_adaptive_mean", stone_bw_variations.adaptive_mean(gray)),
            ("03_adaptive_gaussian", stone_bw_variations.adaptive_gaussian(gray)),
            ("04_clean_light", stone_bw_variations.full_clean_pipeline(gray, denoise_strength=8, min_component_size=30)),
            ("05_clean_medium", stone_bw_variations.full_clean_pipeline(gray, denoise_strength=15, min_component_size=60)),
            ("06_clean_aggressive", stone_bw_variations.full_clean_pipeline(gray, denoise_strength=22, min_component_size=100)),
            ("07_clean_bold", stone_bw_variations.full_clean_pipeline(gray, denoise_strength=15, min_component_size=60, bold=True)),
        ]
        
        # Save output images as base64 strings in response
        results = {}
        for name, out_img in variations:
            results[name] = to_base64_data_url(out_img, ".png")
            
        # Generate contact sheet in-memory
        # Recreate make_contact_sheet logic to return base64
        thumbs = []
        thumb_width = 500
        for label, var_img in variations:
            vh, vw = var_img.shape[:2]
            scale = thumb_width / vw
            thumb = cv2.resize(var_img, (thumb_width, int(vh * scale)))
            thumb_bgr = cv2.cvtColor(thumb, cv2.COLOR_GRAY2BGR)
            cv2.putText(thumb_bgr, label, (8, 22), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 0, 255), 2, cv2.LINE_AA)
            thumbs.append(thumb_bgr)

        cols = 2
        rows = (len(thumbs) + cols - 1) // cols
        th, tw = thumbs[0].shape[:2]
        sheet = np.full((th * rows, tw * cols, 3), 255, dtype=np.uint8)
        for idx, thumb in enumerate(thumbs):
            r, c = divmod(idx, cols)
            sheet[r * th:(r + 1) * th, c * tw:(c + 1) * tw] = thumb
            
        contact_sheet_base64 = to_base64_data_url(sheet, ".png")
        
        return JSONResponse({
            "success": True,
            "raw_image": raw_base64,
            "variations": results,
            "contact_sheet": contact_sheet_base64
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")

# Mount frontend static files route (must be mounted last)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Vercel needs standard run, locally run on port 8050
    uvicorn.run(app, host="127.0.0.1", port=8050)
