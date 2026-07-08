FROM python:3.11-slim

# Install system dependencies for OpenCV and clean apt cache
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create outputs and static directories to ensure they exist
RUN mkdir -p /app/outputs /app/static

# Expose default port (Hugging Face Spaces uses 7860, Render injects PORT)
EXPOSE 7860

# Command to launch the server dynamically binding to port 7860 or PORT env var
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
