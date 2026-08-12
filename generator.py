import sys
import io
import os
import json
import asyncio
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Force stdout/stderr to UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, vfx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# High-resolution vertical royalty-free Stoic background images (Unsplash CDN)
STOIC_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1552832230-c0197dd311b5?fit=crop&w=1080&h=1920&q=80",  # Rome Colosseum
    "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?fit=crop&w=1080&h=1920&q=80",  # Roman Ruins
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?fit=crop&w=1080&h=1920&q=80",  # Dark Atmospheric Forest
    "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?fit=crop&w=1080&h=1920&q=80",  # Cosmic Night Sky
    "https://images.unsplash.com/photo-1534447677768-be436bb09401?fit=crop&w=1080&h=1920&q=80"   # Epic Stoic Mountain Peak
]

def ensure_bg_images():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for i, url in enumerate(STOIC_IMAGE_URLS):
        img_path = os.path.join(ASSETS_DIR, f"stoic_bg_{i}.jpg")
        if not os.path.exists(img_path) or os.path.getsize(img_path) < 10000:
            try:
                print(f"[+] HD Stoic Görsel İndiriliyor #{i+1}...")
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    with open(img_path, "wb") as f:
                        f.write(resp.content)
            except Exception as e:
                print(f"[!] Görsel indirilemedi: {e}")

def generate_voiceover(text, voice_path):
    print("[+] YZ Seslendirme olusturuluyor (Edge-TTS - en-US-ChristopherNeural)...")
    async def amake():
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(voice_path)
    asyncio.run(amake())
    return voice_path

def create_tight_text_image(text, max_width=900, font_size=56, text_color="white", bg_color=(0, 0, 0, 210), stroke_color="black"):
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    dummy = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)

    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    line_height = font_size + 20
    max_line_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_line_w:
            max_line_w = w

    pad = 24
    box_w = max_line_w + (pad * 2)
    box_h = (len(lines) * line_height) + pad

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_color:
        draw.rounded_rectangle([0, 0, box_w, box_h], radius=16, fill=bg_color)

    stroke_w = 4
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lx = (box_w - lw) // 2
        ly = (pad // 2) + (i * line_height)

        for sx in range(-stroke_w, stroke_w + 1):
            for sy in range(-stroke_w, stroke_w + 1):
                draw.text((lx + sx, ly + sy), line, font=font, fill=stroke_color)

        draw.text((lx, ly), line, font=font, fill=text_color)

    return np.array(img)

def split_text_into_phrases(full_text, max_words=5):
    words = full_text.split()
    phrases = []
    for i in range(0, len(words), max_words):
        phrases.append(" ".join(words[i:i+max_words]))
    return phrases

def create_video_from_template(template_data, index):
    print(f"\n==========================================")
    print(f"[+] Video #{index + 1} Isleniyor: {template_data['title']}")
    print(f"==========================================")

    ensure_bg_images()

    video_id = f"video_{index+1}_{template_data['id']}"
    mp3_path = os.path.join(ASSETS_DIR, f"{video_id}.mp3")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
    metadata_txt = os.path.join(OUTPUT_DIR, f"{video_id}_METADATA.txt")

    # 1. Seslendirme
    generate_voiceover(template_data['script_body'], mp3_path)
    audio = AudioFileClip(mp3_path)
    audio_duration = audio.duration
    print(f"[+] Ses Suresi: {audio_duration:.2f} saniye")

    # 2. HD Sinematik Stoik Görsel Arka Plan
    bg_img_path = os.path.join(ASSETS_DIR, f"stoic_bg_{index % len(STOIC_IMAGE_URLS)}.jpg")
    print(f"[+] HD Arka Plan Görseli Yükleniyor: {bg_img_path}")
    
    bg_clip = ImageClip(bg_img_path).with_duration(audio_duration).resized((1080, 1920))

    overlay_clips = [bg_clip]

    # Sinematik Karartma Katmani (Okunabilirlik ve atmosfer icin %45 Opacity)
    dark_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.45).with_duration(audio_duration)
    overlay_clips.append(dark_overlay)

    # Ust Baslik Banner (Gold Renk) - Top Center (y=240)
    title_img = create_tight_text_image(template_data['caption_title'], font_size=60, text_color="#FFD700")
    title_clip = ImageClip(title_img).with_duration(audio_duration).with_position(("center", 240))
    overlay_clips.append(title_clip)

    # Dinamik Altyazi Klipleri - Lower Center (y=1250)
    phrases = split_text_into_phrases(template_data['script_body'], max_words=5)
    phrase_duration = audio_duration / len(phrases)

    for i, phrase in enumerate(phrases):
        start_t = i * phrase_duration
        color = "#FFD700" if i % 2 == 0 else "#FFFFFF"
        sub_img = create_tight_text_image(phrase, font_size=52, text_color=color)
        sub_clip = ImageClip(sub_img).with_start(start_t).with_duration(phrase_duration).with_position(("center", 1250))
        overlay_clips.append(sub_clip)

    # Birlesdirme ve Render
    final_video = CompositeVideoClip(overlay_clips).with_audio(audio).with_duration(audio_duration)
    
    print(f"[+] MP4 Render Ediliyor -> {output_mp4}")
    final_video.write_videofile(
        output_mp4,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast",
        threads=4
    )

    final_video.close()
    audio.close()
    bg_clip.close()

    # Metadata Yayinlama Dosyasi
    with open(metadata_txt, "w", encoding="utf-8") as f:
        f.write(f"====================================================\n")
        f.write(f"VIDEO #{index+1} YAYINLAMA METADATASI\n")
        f.write(f"====================================================\n\n")
        f.write(f"VIDEO BASLIGI (Title):\n{template_data['title']}\n\n")
        f.write(f"VIDEO ACIKLAMASI (Description):\n{template_data['script_body']}\n\n#stoicism #mindset #motivation #shorts #viral\n\n")
        f.write(f"SABITLENECEK YORUM (Pinned Comment):\n{template_data['pinned_comment']}\n\n")
        f.write(f"====================================================\n")

    print(f"[+] VIDEO #{index+1} BASARIYLA URETILDI!")
    return output_mp4

def main():
    print("[+] YAPAY ZEKA SHORTS FABRIKASI CALISTIRILIYOR...")
    templates_path = os.path.join(BASE_DIR, "templates.json")
    
    with open(templates_path, "r", encoding="utf-8") as f:
        templates = json.load(f)

    num_videos = min(3, len(templates))
    generated_files = []

    for i in range(num_videos):
        mp4_path = create_video_from_template(templates[i], i)
        generated_files.append(mp4_path)

    print("\n[+] TEBRILER! TUM VIDEOLAR URETILDI!")
    print(f"[+] Olusturulan MP4 ve Metadata dosyalari 'output_videos' klasorunde hazir:")
    for file in generated_files:
        print(f" - {file}")

if __name__ == "__main__":
    main()
