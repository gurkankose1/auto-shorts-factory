import sys
import io
import os
import json
import asyncio
import requests
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Safely reconfigure stdout/stderr encoding without closing underlying buffer
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, CompositeAudioClip, vfx
from download_niche_moving_videos_github import ensure_niche_moving_videos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
VIDEO_ASSETS_DIR = os.path.join(ASSETS_DIR, "moving_videos")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(VIDEO_ASSETS_DIR, exist_ok=True)

def get_niche_config(niche_key="stoic"):
    configs = {
        "stoic": {"voice": "en-US-ChristopherNeural", "prefix": "stoic_bg_"},
        "bible": {"voice": "en-US-GuyNeural", "prefix": "bible_bg_"},
        "health": {"voice": "en-US-JennyNeural", "prefix": "health_bg_"},
        "kids": {"voice": "en-US-AnaNeural", "prefix": "kids_bg_"}
    }
    return configs.get(niche_key, configs["stoic"])

def get_moving_video(niche_key="stoic", index=0):
    ensure_niche_moving_videos()
    if os.path.exists(VIDEO_ASSETS_DIR):
        files = [os.path.join(VIDEO_ASSETS_DIR, f) for f in os.listdir(VIDEO_ASSETS_DIR) if f.startswith(niche_key) and f.endswith(".mp4")]
        if files:
            return files[index % len(files)]
    return None

def get_niche_bg_images(niche_prefix="stoic_bg_"):
    matching_paths = []
    for i in range(5):
        img_name = f"{niche_prefix}{i}.jpg"
        img_path = os.path.join(ASSETS_DIR, img_name)
        if os.path.exists(img_path) and os.path.getsize(img_path) > 10000:
            matching_paths.append(img_path)
    
    if not matching_paths:
        for i in range(5):
            img_path = os.path.join(ASSETS_DIR, f"stoic_bg_{i}.jpg")
            if os.path.exists(img_path):
                matching_paths.append(img_path)
    return matching_paths

def generate_voiceover_with_sync(text, voice_path, voice_name="en-US-ChristopherNeural"):
    print(f"[+] YZ Seslendirme ve Milisaniye Senkronizasyonu Olusturuluyor ({voice_name})...")
    sentence_boundaries = []
    
    async def amake():
        communicate = edge_tts.Communicate(text, voice_name)
        with open(voice_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    start_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    sentence_boundaries.append({
                        "text": chunk["text"],
                        "start": start_sec,
                        "duration": dur_sec
                    })
    
    asyncio.run(amake())
    return sentence_boundaries

def create_tight_text_image(text, max_width=960, font_size=76, text_color="#FFFF00", bg_color=(0, 0, 0, 240), stroke_color="black"):
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

    text_upper = text.upper()
    words = text_upper.split()
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

    pad_x = 36
    pad_y = 20
    box_w = max_line_w + (pad_x * 2)
    box_h = (len(lines) * line_height) + (pad_y * 2)

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_color:
        draw.rounded_rectangle([0, 0, box_w, box_h], radius=24, fill=bg_color)

    stroke_w = 6
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

def create_video_from_template(template_data, index, niche_key="stoic"):
    clean_title = template_data['title'].encode('ascii', errors='ignore').decode('ascii')
    print(f"\n==========================================")
    print(f"[+] Video #{index + 1} Isleniyor [{niche_key.upper()}]: {clean_title}")
    print(f"==========================================")

    niche_cfg = get_niche_config(niche_key)

    video_id = f"video_{index+1}_{template_data['id']}"
    mp3_path = os.path.join(ASSETS_DIR, f"{video_id}.mp3")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")

    # 1. YZ Seslendirme ve Milisaniye Has Senkronizasyon Verisi
    sentence_boundaries = generate_voiceover_with_sync(template_data['script_body'], mp3_path, niche_cfg["voice"])
    voice_audio = AudioFileClip(mp3_path)
    audio_duration = voice_audio.duration
    print(f"[+] Ses Suresi: {audio_duration:.2f} saniye")

    final_audio = voice_audio

    # 2. Gerçek Hareketli MP4 Stok Video Arka Planı (Moving Background Video)
    moving_video_file = get_moving_video(niche_key, index=index)
    overlay_clips = []

    if moving_video_file and os.path.exists(moving_video_file):
        try:
            print(f"[+] Video #{index+1} Icin Gercek Hareketli MP4 Stok Video Secildi: {moving_video_file}")
            raw_bg = VideoFileClip(moving_video_file)
            if raw_bg.duration < audio_duration:
                raw_bg = raw_bg.with_effects([vfx.Loop(duration=audio_duration)])
            else:
                raw_bg = raw_bg.subclipped(0, audio_duration)
            
            # Crop to 1080x1920 portrait
            raw_bg = raw_bg.resized(height=1920)
            if raw_bg.w < 1080:
                raw_bg = raw_bg.resized(width=1080)
            bg_video_clip = raw_bg.cropped(x_center=raw_bg.w/2, y_center=raw_bg.h/2, width=1080, height=1920)
            overlay_clips.append(bg_video_clip)
        except Exception as e:
            print(f"[!] Hareketli video yukleme hatası, görsele düşülüyor: {e}")
            overlay_clips = []

    # Fallback to image slideshow if no video clip
    if not overlay_clips:
        bg_images = get_niche_bg_images(niche_cfg["prefix"])
        num_slides = 3
        slide_dur = audio_duration / num_slides
        bg_clips = []
        for s in range(num_slides):
            img_idx = (index * num_slides + s) % len(bg_images)
            img_path = bg_images[img_idx]
            start_time = s * slide_dur
            dur = slide_dur if s < num_slides - 1 else (audio_duration - start_time)
            slide_clip = ImageClip(img_path).resized((1080, 1920)).with_start(start_time).with_duration(dur)
            bg_clips.append(slide_clip)
        overlay_clips = list(bg_clips)

    # Sinematik Karartma Katmani (%45 Opacity)
    dark_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.45).with_duration(audio_duration)
    overlay_clips.append(dark_overlay)

    # Ust Baslik Banner (Büyük Altın Renk) - Top Center (y=180)
    title_img = create_tight_text_image(template_data['caption_title'], font_size=72, text_color="#FFD700")
    title_clip = ImageClip(title_img).with_duration(audio_duration).with_position(("center", 180))
    overlay_clips.append(title_clip)

    # Milisaniye Has Senkronize Kinetik Altyazı Katmanları (100% Perfect Audio-Visual Sync)
    color_palette = ["#FFFF00", "#00FF88", "#FFFFFF", "#FFD700"]
    phrase_count = 0

    if sentence_boundaries:
        for sb in sentence_boundaries:
            s_text = sb["text"]
            s_start = sb["start"]
            s_dur = sb["duration"]
            words = s_text.split()
            
            # Split sentence into 2-word phrase chunks
            chunks = [" ".join(words[k:k+2]) for k in range(0, len(words), 2)]
            chunk_dur = s_dur / max(1, len(chunks))
            
            for k, chunk in enumerate(chunks):
                phrase_start = s_start + (k * chunk_dur)
                color = color_palette[phrase_count % len(color_palette)]
                phrase_count += 1
                
                sub_img = create_tight_text_image(chunk, font_size=76, text_color=color)
                sub_clip = ImageClip(sub_img).with_start(phrase_start).with_duration(chunk_dur).with_position(("center", 1200))
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
