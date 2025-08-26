#!/bin/bash
echo "Checking system dependencies..."
# FFmpeg kontrolü - Render'da genellikle zaten kurulu
if ! command -v ffmpeg &> /dev/null; then
    echo "WARNING: FFmpeg not found! Audio conversion may not work properly."
else
    echo "FFmpeg is available"
fi

echo "Starting ZB MUSIC Bot..."
python reis_bot.py
