import os
import sys
import uuid
import shutil
import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure the current directory is in python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

import stone_bw_variations

app = FastAPI(title="Stone Inscription Preprocessor Server")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output and Static directories setup
OUTPUTS_DIR = os.path.join(CURRENT_DIR, "outputs")
STATIC_DIR = os.path.join(CURRENT_DIR, "static")

os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp')):
        raise HTTPException(status_code=400, detail="Invalid image file format.")
    
    # Create unique session ID
    session_id = uuid.uuid4().hex
    session_dir = os.path.join(OUTPUTS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Save raw uploaded image
    input_filename = f"raw_{file.filename}"
    input_path = os.path.join(session_dir, input_filename)
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Load image as grayscale
        gray = stone_bw_variations.load_gray(input_path, upscale=1.5)
        
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
        
        # Save output images
        results = {}
        for name, out_img in variations:
            filename = f"{name}.png"
            filepath = os.path.join(session_dir, filename)
            cv2.imwrite(filepath, out_img)
            results[name] = f"/outputs/{session_id}/{filename}"
            
        # Make contact sheet
        contact_sheet_filename = "contact_sheet.png"
        contact_sheet_path = os.path.join(session_dir, contact_sheet_filename)
        stone_bw_variations.make_contact_sheet(variations, contact_sheet_path)
        
        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "raw_image": f"/outputs/{session_id}/{input_filename}",
            "variations": results,
            "contact_sheet": f"/outputs/{session_id}/{contact_sheet_filename}"
        })
        
    except Exception as e:
        # Cleanup directory on failure
        shutil.rmtree(session_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")

# Mount outputs static files route
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")

# Mount frontend static files route (must be mounted last)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8050)
