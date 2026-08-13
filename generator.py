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
if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.closed:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, CompositeAudioClip, vfx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Default Stoic background images fallback
STOIC_IMAGE_URLS = [
    "https://images.unsplash.com/photo-1552832230-c0197dd311b5?fit=crop&w=1080&h=1920&q=80",
    "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?fit=crop&w=1080&h=1920&q=80",
    "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?fit=crop&w=1080&h=1920&q=80",
    "https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?fit=crop&w=1080&h=1920&q=80",
    "https://images.unsplash.com/photo-1534447677768-be436bb09401?fit=crop&w=1080&h=1920&q=80"
]

MUSIC_URL = "https://cdn.pixabay.com/audio/2022/05/27/audio_1808fbf07a.mp3"

def get_niche_config(niche_key="stoic"):
    configs = {
        "stoic": {"voice": "en-US-ChristopherNeural", "prefix": "stoic_bg_"},
        "bible": {"voice": "en-US-GuyNeural", "prefix": "bible_bg_"},
        "health": {"voice": "en-US-JennyNeural", "prefix": "health_bg_"},
        "kids": {"voice": "en-US-AnaNeural", "prefix": "kids_bg_"}
    }
    return configs.get(niche_key, configs["stoic"])

def get_niche_bg_images(niche_prefix="stoic_bg_"):
    matching_paths = []
    for i in range(5):
        img_name = f"{niche_prefix}{i}.jpg"
        img_path = os.path.join(ASSETS_DIR, img_name)
        if os.path.exists(img_path) and os.path.getsize(img_path) > 10000:
            matching_paths.append(img_path)
    
    # Fallback to stoic_bg_ if niche images missing
    if not matching_paths:
        for i in range(5):
            img_path = os.path.join(ASSETS_DIR, f"stoic_bg_{i}.jpg")
            if os.path.exists(img_path):
                matching_paths.append(img_path)
    return matching_paths

def generate_voiceover(text, voice_path, voice_name="en-US-ChristopherNeural"):
    print(f"[+] YZ Seslendirme olusturuluyor ({voice_name})...")
    async def amake():
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(voice_path)
    asyncio.run(amake())
    return voice_path

def create_tight_text_image(text, max_width=960, font_size=72, text_color="white", bg_color=(0, 0, 0, 230), stroke_color="black"):
    font = None
    custom_font_path = os.path.join(ASSETS_DIR, "font.ttf")
    if os.path.exists(custom_font_path):
        try:
            font = ImageFont.truetype(custom_font_path, font_size)
        except Exception:
            font = None

    if font is None:
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

    line_height = font_size + 24
    max_line_w = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_line_w:
            max_line_w = w

    pad_x = 32
    pad_y = 20
    box_w = max_line_w + (pad_x * 2)
    box_h = (len(lines) * line_height) + (pad_y * 2)

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_color:
        draw.rounded_rectangle([0, 0, box_w, box_h], radius=20, fill=bg_color)

    stroke_w = 5
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lx = (box_w - lw) // 2
        ly = pad_y + (i * line_height)

        for sx in range(-stroke_w, stroke_w + 1):
            for sy in range(-stroke_w, stroke_w + 1):
                draw.text((lx + sx, ly + sy), line, font=font, fill=stroke_color)

        draw.text((lx, ly), line, font=font, fill=text_color)

    return np.array(img)

def split_text_into_phrases(full_text, max_words=4):
    words = full_text.split()
    phrases = []
    for i in range(0, len(words), max_words):
        phrases.append(" ".join(words[i:i+max_words]))
    return phrases

def create_video_from_template(template_data, index, niche_key="stoic"):
    print(f"\n==========================================")
    print(f"[+] Video #{index + 1} Isleniyor [{niche_key.upper()}]: {template_data['title']}")
    print(f"==========================================")

    niche_cfg = get_niche_config(niche_key)
    bg_images = get_niche_bg_images(niche_cfg["prefix"])
    music_path = os.path.join(ASSETS_DIR, "stoic_bg_music.mp3")

    video_id = f"video_{index+1}_{template_data['id']}"
    mp3_path = os.path.join(ASSETS_DIR, f"{video_id}.mp3")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
    metadata_txt = os.path.join(OUTPUT_DIR, f"{video_id}_METADATA.txt")

    # 1. YZ Seslendirme (Niş Özel Ses) & Sinematik Arka Plan Müzik Miksi
    generate_voiceover(template_data['script_body'], mp3_path, niche_cfg["voice"])
    voice_audio = AudioFileClip(mp3_path)
    audio_duration = voice_audio.duration
    print(f"[+] Ses Suresi: {audio_duration:.2f} saniye")

    final_audio = voice_audio
    if os.path.exists(music_path):
        try:
            bg_music = AudioFileClip(music_path)
            if bg_music.duration < audio_duration:
                bg_music = bg_music.with_effects([vfx.Loop(duration=audio_duration)])
            else:
                bg_music = bg_music.subclipped(0, audio_duration)
            bg_music = bg_music.with_volume(0.12)
            final_audio = CompositeAudioClip([voice_audio, bg_music])
            print("[+] Sinematik Arka Plan Muzigi Basariyla Harmanlandi (%12 Ses Seviyesi)")
        except Exception as e:
            print(f"[!] Müzik miks hatası: {e}")

    # 2. Dinamik 3 Görselli Slayt (Niş Özel Görseller)
    num_slides = 3
    slide_dur = audio_duration / num_slides
    bg_clips = []

    for s in range(num_slides):
        img_idx = (index * num_slides + s) % len(bg_images)
        img_path = bg_images[img_idx]
        start_time = s * slide_dur
        dur = slide_dur if s < num_slides - 1 else (audio_duration - start_time)
        
        slide_clip = (
            ImageClip(img_path)
            .resized((1080, 1920))
            .with_start(start_time)
            .with_duration(dur)
        )
        bg_clips.append(slide_clip)

    overlay_clips = list(bg_clips)

    # Sinematik Karartma Katmani (%45 Opacity)
    dark_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.45).with_duration(audio_duration)
    overlay_clips.append(dark_overlay)

    # Ust Baslik Banner (Büyük Altın Renk) - Top Center (y=180)
    title_img = create_tight_text_image(template_data['caption_title'], font_size=68, text_color="#FFD700")
    title_clip = ImageClip(title_img).with_duration(audio_duration).with_position(("center", 180))
    overlay_clips.append(title_clip)

    # Dinamik Altyazi Klipleri (Dev Boyut, Sarı/Beyaz Parlayan) - Lower Center (y=1250)
    phrases = split_text_into_phrases(template_data['script_body'], max_words=4)
    phrase_duration = audio_duration / len(phrases)

    for i, phrase in enumerate(phrases):
        start_t = i * phrase_duration
        color = "#FFD700" if i % 2 == 0 else "#FFFFFF"
        sub_img = create_tight_text_image(phrase, font_size=64, text_color=color)
        sub_clip = ImageClip(sub_img).with_start(start_t).with_duration(phrase_duration).with_position(("center", 1250))
        overlay_clips.append(sub_clip)

    # Birlesdirme ve Render
    final_video = CompositeVideoClip(overlay_clips).with_audio(final_audio).with_duration(audio_duration)
    
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
    voice_audio.close()
    for c in bg_clips:
        c.close()

    return output_mp4

def main(niche_key="stoic"):
    print(f"[+] YAPAY ZEKA SHORTS FABRIKASI CALISTIRILIYOR [{niche_key.upper()}]...")
    templates_path = os.path.join(BASE_DIR, "templates.json")
    
    with open(templates_path, "r", encoding="utf-8") as f:
        templates = json.load(f)

    num_videos = min(3, len(templates))
    generated_files = []

    for i in range(num_videos):
        mp4_path = create_video_from_template(templates[i], i, niche_key=niche_key)
        generated_files.append(mp4_path)

    print("\n[+] TEBRILER! TUM VIDEOLAR URETILDI!")
    for file in generated_files:
        print(f" - {file}")

if __name__ == "__main__":
    main()
