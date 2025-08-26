#!/bin/bash
# FFmpeg kontrolü
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found! Installing..."
    apt-get update && apt-get install -y ffmpeg
fi

echo "Starting ZB MUSIC Bot..."
python reis_bot.py
