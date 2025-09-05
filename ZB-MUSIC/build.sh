#!/bin/bash
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Checking for ffmpeg..."
# Render'da ffmpeg zaten kurulu geliyor, kontrol edelim
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found! This might cause issues with audio conversion."
else
    echo "FFmpeg is available: $(ffmpeg -version | head -n1)"
fi

echo "Build completed successfully!"
