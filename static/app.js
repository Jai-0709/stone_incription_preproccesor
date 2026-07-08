document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const browseBtn = document.getElementById("browse-btn");
    const uploadSection = document.getElementById("upload-section");
    const loadingOverlay = document.getElementById("loading-overlay");
    const resultsSection = document.getElementById("results-section");
    const originalPreview = document.getElementById("original-preview");
    const variationsGrid = document.getElementById("variations-grid");
    const resetBtn = document.getElementById("reset-btn");
    const downloadSheetBtn = document.getElementById("download-sheet-btn");
    const uploadedFilename = document.getElementById("uploaded-filename");

    // --- Variation Details Metadata ---
    const VARIATION_DETAILS = {
        "01_otsu_global": {
            name: "Global Otsu Threshold",
            desc: "Applies a single global threshold computed automatically. Best for clean printouts or perfectly uniform lighting.",
            params: "Gaussian Blur (5x5) ➔ Threshold: Otsu"
        },
        "02_adaptive_mean": {
            name: "Adaptive Mean",
            desc: "Thresholds pixels based on the local neighborhood mean. Compensates for simple illumination gradients.",
            params: "Median Blur (5) ➔ BlockSize: 35, C: 10"
        },
        "03_adaptive_gaussian": {
            name: "Adaptive Gaussian",
            desc: "Thresholds pixels using a weighted Gaussian sum of the neighborhood. Yields cleaner character borders.",
            params: "Median Blur (5) ➔ BlockSize: 35, C: 10"
        },
        "04_clean_light": {
            name: "Clean Light Denoise",
            desc: "Full preprocessing pipeline with light non-local means denoising to retain fine details on smooth stones.",
            params: "CLAHE (2.5) ➔ Denoise H: 8 ➔ Min Component: 30"
        },
        "05_clean_medium": {
            name: "Clean Medium Denoise",
            desc: "Our standard balanced preprocessing. Denoises texture grain while preserving actual carved inscriptions.",
            params: "CLAHE (2.5) ➔ Denoise H: 15 ➔ Min Component: 60"
        },
        "06_clean_aggressive": {
            name: "Clean Aggressive Denoise",
            desc: "Filters heavy stone wear and surface cracks. Keeps only deep, prominent character grooves.",
            params: "CLAHE (2.5) ➔ Denoise H: 22 ➔ Min Component: 100"
        },
        "07_clean_bold": {
            name: "Clean Bold Strokes",
            desc: "Medium cleanup pipeline combined with dilation to widen and bolden characters. Perfect for thin carvings.",
            params: "Medium Pipeline ➔ Dilate (2x2 Ellipse, Iter: 1)"
        }
    };

    // --- Upload Handlers ---
    browseBtn.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // --- Drag and Drop Handlers ---
    ["dragenter", "dragover"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
        }, false);
    });

    dropZone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // --- Reset Handler ---
    resetBtn.addEventListener("click", () => {
        fileInput.value = "";
        resultsSection.classList.add("hidden");
        uploadSection.classList.remove("hidden");
        variationsGrid.innerHTML = "";
    });

    // --- File Processor ---
    function handleFile(file) {
        // Validate it's an image
        if (!file.type.startsWith("image/")) {
            alert("Please upload a valid image file.");
            return;
        }

        // Show loading spinner
        loadingOverlay.classList.remove("hidden");

        const formData = new FormData();
        formData.append("file", file);

        fetch("/process", {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || "Server error occurred"); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                renderResults(file.name, data);
            } else {
                throw new Error("Failed to process image.");
            }
        })
        .catch(error => {
            console.error(error);
            alert(`Error: ${error.message}`);
        })
        .finally(() => {
            loadingOverlay.classList.add("hidden");
        });
    }

    // --- Render Results UI ---
    function renderResults(filename, data) {
        uploadedFilename.textContent = filename;
        originalPreview.src = data.raw_image;
        downloadSheetBtn.href = data.contact_sheet;

        // Render each variation card
        variationsGrid.innerHTML = "";
        
        // Sorting keys to ensure they print in numerical order
        const sortedKeys = Object.keys(data.variations).sort();
        
        sortedKeys.forEach(key => {
            const imageUrl = data.variations[key];
            const details = VARIATION_DETAILS[key] || { name: key, desc: "B/W Variation", params: "" };
            const card = document.createElement("div");
            card.className = "variation-card";

            card.innerHTML = `
                <div class="var-header">
                    <h4>${details.name}</h4>
                    <span class="var-badge">PNG</span>
                </div>
                <div class="var-image-container" onclick="openFullscreen('${imageUrl}')">
                    <img src="${imageUrl}" alt="${details.name}">
                </div>
                <div class="var-meta">
                    <p>${details.desc}</p>
                    <span>➔ ${details.params}</span>
                </div>
                <a href="${imageUrl}" download="${key}_${filename}.png" class="btn btn-card-download">
                    <i class="fa-solid fa-download"></i> Download B/W
                </a>
            `;
            variationsGrid.appendChild(card);
        });

        // Toggle Views
        uploadSection.classList.add("hidden");
        resultsSection.classList.remove("hidden");
    }
});

// Fullscreen Viewer Helper
function openFullscreen(url) {
    const w = window.open();
    w.document.write(`<body style="margin:0;background:#0b0f19;display:flex;align-items:center;justify-content:center;height:100vh;"><img src="${url}" style="max-width:100%;max-height:100%;object-fit:contain;border:1px solid #1f2937;"></body>`);
}
