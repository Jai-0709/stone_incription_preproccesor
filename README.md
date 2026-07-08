# Stone Inscription Preprocessor & B/W Tuner

A standalone web application and Python library designed to process raw stone-inscription photographs into multiple optimized black-and-white variations. This tool allows researchers and developers to visually compare different image-cleanup pipelines and choose/download the best result for dataset curation or OCR pipelines.

## Features
* **7 Preprocessing Pipelines:** Includes Global Otsu, Adaptive Mean/Gaussian, and custom multi-step cleanup pipelines (incorporating CLAHE contrast boosting, non-local means denoising, top-hat morphology, and character stroke bolding).
* **Drag-and-Drop Web Interface:** Premium glassmorphic interface built using FastAPI, HTML5, Vanilla CSS, and JavaScript.
* **Interactive Previews:** View the original image alongside all variations in a responsive grid. Click to inspect high-resolution images.
* **Direct Individual Downloads:** Download any processed variation with a single click.
* **Tiled Contact Sheet:** Automatically tiles all 7 variations together into a single comparison sheet.

## Tech Stack
* **Backend:** FastAPI (Python), Uvicorn, OpenCV, NumPy
* **Frontend:** HTML5, Vanilla CSS (Design Tokens, Dark Mode, Micro-animations), Vanilla JavaScript

## Setup & Running Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python main.py
   ```

3. **Access the application:**
   Open [http://localhost:8050](http://localhost:8050) in your browser.

## Project Structure
* `main.py`: FastAPI server serving endpoints & static client.
* `stone_bw_variations.py`: Core image processing module.
* `static/`: Contains HTML, CSS, and JavaScript files.
* `outputs/`: Saved session files (excluded from Git).
