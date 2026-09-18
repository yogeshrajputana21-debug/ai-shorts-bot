import os
import re
import json
import asyncio
import subprocess
import requests
import feedparser
import whisper
import edge_tts
import streamlit as st
from google import genai
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Read keys from Streamlit Secrets or Environment
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
PEXELS_API_KEY = st.secrets.get("PEXELS_API_KEY", os.getenv("PEXELS_API_KEY"))
VOICE = st.secrets.get("VOICE", "en-US-ChristopherNeural")

ai_client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_top_trends(geo="US"):
    feed = feedparser.parse(f"https://trends.google.com/trending/rss?geo={geo}")
    return [e.title for e in feed.entries[:10]] if feed.entries else ["AI Breakthroughs"]

def generate_script(topic):
    prompt = f"""
    You are an expert short-form video creator. Write a compelling 30-to-40 second script about: "{topic}".
    Requirements:
    - Line 1 must be a viral hook grabbing attention instantly.
    - Word count strictly between 60 and 80 words.
    - Do NOT include scene directions, bracketed cues, emojis, or markdown headers.
    - Output ONLY the spoken text.
    """
    response = ai_client.models.generate_content(
                model="gemini-3.6-flash",
        contents=prompt
    )
    return re.sub(r'[*_#]', '', response.text).strip().replace('\n', ' ')

async def create_voiceover(text, audio_out="voice.mp3"):
    tts = edge_tts.Communicate(text, VOICE)
    await tts.save(audio_out)

def generate_subtitles_ass(audio_path="voice.mp3", ass_out="subtitles.ass"):
    model = whisper.load_model("base")
    result = model.transcribe(audio_path, word_timestamps=True)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Impact,80,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,5,30,30,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h:01d}:{m:02d}:{s:02d}.{cs:02d}"

    events = []
    for segment in result["segments"]:
        for word_info in segment.get("words", []):
            start = format_time(word_info["start"])
            end = format_time(word_info["end"])
            word = word_info["word"].strip().upper()
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{word}")

    with open(ass_out, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

def fetch_background_video(query="neon abstract cinematic", output_video="bg.mp4"):
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=3"
    r = requests.get(url, headers=headers).json()
    
    if not r.get("videos"):
        query = "cinematic nature"
        r = requests.get(f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=3", headers=headers).json()

    video_files = r["videos"][0]["video_files"]
    video_url = next(v["link"] for v in video_files if v["width"] == 1080 or "hd" in v.get("quality", ""))

    with requests.get(video_url, stream=True) as stream, open(output_video, "wb") as f:
        for chunk in stream.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)

def render_video_ffmpeg(audio_file="voice.mp3", bg_file="bg.mp4", sub_file="subtitles.ass", output="final_short.mp4"):
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_file
    ])
    duration = float(probe.strip())

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", bg_file,
        "-i", audio_file,
        "-t", str(duration),
        "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass={sub_file}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", output
    ]
    subprocess.run(cmd, check=True)
