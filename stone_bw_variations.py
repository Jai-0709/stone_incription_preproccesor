"""
stone_bw_variations.py

Converts a raw stone-inscription photo into SEVERAL different black-and-white
cleanup variations, so you can visually compare and pick the one that reads
best for your dataset/pipeline, instead of committing to one fixed method.

Usage:
    python3 stone_bw_variations.py input.jpg output_dir/

Produces (in output_dir/):
    01_otsu_global.png          - simple global Otsu threshold
    02_adaptive_mean.png        - adaptive mean threshold
    03_adaptive_gaussian.png    - adaptive gaussian threshold
    04_clean_light.png          - full cleanup pipeline, light denoise
    05_clean_medium.png         - full cleanup pipeline, medium denoise
    06_clean_aggressive.png     - full cleanup pipeline, aggressive denoise
    07_clean_bold.png           - medium cleanup + bolded strokes
    contact_sheet.png           - all variations tiled together for quick comparison
"""

import sys
import os
import cv2
import numpy as np


def load_gray(path, upscale=1.5, max_width=1800):
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    # Cap working resolution so denoising stays fast on large phone/camera photos
    if w * upscale > max_width:
        upscale = max_width / w
    if upscale != 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    return gray


def clear_borders(binary_inv, border_margin=10):
    """Remove connected components touching the image edges (shadows, borders)."""
    h, w = binary_inv.shape
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_inv, connectivity=8)
    clean = np.zeros_like(binary_inv)
    for i in range(1, num_labels):
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        sw = stats[i, cv2.CC_STAT_WIDTH]
        sh = stats[i, cv2.CC_STAT_HEIGHT]
        
        # Check if component touches the border
        touches_border = (
            x <= border_margin or 
            y <= border_margin or 
            x + sw >= w - border_margin or 
            y + sh >= h - border_margin
        )
        if not touches_border:
            clean[labels == i] = 255
    return clean


def otsu_global(gray):
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, out = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Clear borders by inverting, clearing, and inverting back
    inv = cv2.bitwise_not(out)
    clean_inv = clear_borders(inv)
    return cv2.bitwise_not(clean_inv)


def adaptive_mean(gray):
    blur = cv2.medianBlur(gray, 5)
    binary = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 35, 10
    )
    inv = cv2.bitwise_not(binary)
    clean_inv = clear_borders(inv)
    return cv2.bitwise_not(clean_inv)


def adaptive_gaussian(gray):
    blur = cv2.medianBlur(gray, 5)
    binary = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 10
    )
    inv = cv2.bitwise_not(binary)
    clean_inv = clear_borders(inv)
    return cv2.bitwise_not(clean_inv)


def full_clean_pipeline(
    gray,
    denoise_strength=15,
    clahe_clip=2.5,
    block_size=51,
    threshold_c=12,
    min_component_size=60,
    bold=False,
):
    """Same staged pipeline as stone_preprocessing.py: illumination fix ->
    denoise -> contrast boost -> adaptive threshold -> speckle removal."""
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=25)
    norm = cv2.divide(gray, bg, scale=255)

    denoised = cv2.fastNlMeansDenoising(
        norm, h=denoise_strength, templateWindowSize=7, searchWindowSize=15
    )
    denoised = cv2.bilateralFilter(denoised, d=9, sigmaColor=60, sigmaSpace=60)

    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(16, 16))
    enhanced = clahe.apply(denoised)

    binary = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=block_size, C=threshold_c
    )

    inv = cv2.bitwise_not(binary)
    kernel_pre = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    inv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, kernel_pre, iterations=1)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
    clean_inv = np.zeros_like(inv)
    h, w = inv.shape
    border_margin = 10
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_component_size:
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            sw = stats[i, cv2.CC_STAT_WIDTH]
            sh = stats[i, cv2.CC_STAT_HEIGHT]
            
            touches_border = (
                x <= border_margin or 
                y <= border_margin or 
                x + sw >= w - border_margin or 
                y + sh >= h - border_margin
            )
            if not touches_border:
                clean_inv[labels == i] = 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    clean_inv = cv2.morphologyEx(clean_inv, cv2.MORPH_CLOSE, kernel, iterations=1)

    final = cv2.bitwise_not(clean_inv)
    smooth = cv2.GaussianBlur(final, (3, 3), 0)
    _, final_smooth = cv2.threshold(smooth, 200, 255, cv2.THRESH_BINARY)

    if bold:
        kernel_bold = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        thick_inv = cv2.dilate(cv2.bitwise_not(final_smooth), kernel_bold, iterations=1)
        final_smooth = cv2.bitwise_not(thick_inv)

    return final_smooth


def make_contact_sheet(images_with_labels, out_path, thumb_width=500):
    """Tile all variations into one image with small labels for quick comparison."""
    thumbs = []
    for label, img in images_with_labels:
        h, w = img.shape[:2]
        scale = thumb_width / w
        thumb = cv2.resize(img, (thumb_width, int(h * scale)))
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
    cv2.imwrite(out_path, sheet)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "input.jpg"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "bw_variations"
    os.makedirs(out_dir, exist_ok=True)

    gray = load_gray(src, upscale=1.5)

    variations = [
        ("01_otsu_global", otsu_global(gray)),
        ("02_adaptive_mean", adaptive_mean(gray)),
        ("03_adaptive_gaussian", adaptive_gaussian(gray)),
        ("04_clean_light", full_clean_pipeline(gray, denoise_strength=8, min_component_size=30)),
        ("05_clean_medium", full_clean_pipeline(gray, denoise_strength=15, min_component_size=60)),
        ("06_clean_aggressive", full_clean_pipeline(gray, denoise_strength=22, min_component_size=100)),
        ("07_clean_bold", full_clean_pipeline(gray, denoise_strength=15, min_component_size=60, bold=True)),
    ]

    for name, out_img in variations:
        cv2.imwrite(os.path.join(out_dir, f"{name}.png"), out_img)

    make_contact_sheet(variations, os.path.join(out_dir, "contact_sheet.png"))

    print(f"Wrote {len(variations)} variations + contact sheet to {out_dir}/")


if __name__ == "__main__":
    main()
