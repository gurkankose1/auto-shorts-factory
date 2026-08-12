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

from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Direct royalty-free Pixabay/Pexels HD vertical stock video URLs
STOCK_VIDEO_URLS = [
    "https://cdn.pixabay.com/video/2020/05/25/40149-425149363_large.mp4",
    "https://cdn.pixabay.com/video/2019/04/23/23011-332490807_large.mp4",
    "https://cdn.pixabay.com/video/2021/08/04/83879-584730600_large.mp4"
]

def make_procedural_bg_image(width=1080, height=1920, style_index=0):
    palettes = [
        ((12, 16, 26), (32, 44, 68)),   # Stoic Slate Navy
        ((24, 14, 16), (62, 28, 36)),   # Dark Crimson
        ((15, 15, 15), (45, 45, 45)),   # Dark Onyx
    ]
    c1, c2 = palettes[style_index % len(palettes)]

    y, x = np.ogrid[:height, :width]
    cx, cy = width / 2, height / 2
    r = np.sqrt((x - cx)**2 + (y - cy)**2) / np.sqrt(cx**2 + cy**2)
    r = np.clip(r, 0, 1)

    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for ch in range(3):
        frame[:, :, ch] = (c1[ch] * (1 - r) + c2[ch] * r).astype(np.uint8)

    return frame

def download_bg_video(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 100000:
        return target_path
    try:
        print(f"[+] Stok Video Indiriliyor: {url[:50]}...")
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, stream=True, timeout=10)
        if resp.status_code == 200:
            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            return target_path
    except Exception as e:
        print(f"[!] Indirme atlandi, prosedurel arka plana geciliyor: {e}")
    return None

def generate_voiceover(text, voice_path):
    print("[+] YZ Seslendirme olusturuluyor (Edge-TTS - en-US-ChristopherNeural)...")
    async def amake():
        communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
        await communicate.save(voice_path)
    asyncio.run(amake())
    return voice_path

def create_text_image(text, width=1080, height=1920, font_size=56, text_color="white", highlight_bg=True):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()

    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) > (width - 160):
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    line_height = font_size + 24
    total_text_height = len(lines) * line_height
    start_y = (height - total_text_height) // 2

    for i, line in enumerate(lines):
        y = start_y + (i * line_height)
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2

        if highlight_bg:
            box_pad = 18
            box_coords = [x - box_pad, y - 10, x + text_width + box_pad, y + font_size + 14]
            draw.rectangle(box_coords, fill=(0, 0, 0, 210))

        stroke_w = 4
        for sx in range(-stroke_w, stroke_w + 1):
            for sy in range(-stroke_w, stroke_w + 1):
                draw.text((x + sx, y + sy), line, font=font, fill="black")

        draw.text((x, y), line, font=font, fill=text_color)

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

    video_id = f"video_{index+1}_{template_data['id']}"
    mp3_path = os.path.join(ASSETS_DIR, f"{video_id}.mp3")
    bg_video_path = os.path.join(ASSETS_DIR, f"bg_{index % len(STOCK_VIDEO_URLS)}.mp4")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
    metadata_txt = os.path.join(OUTPUT_DIR, f"{video_id}_METADATA.txt")

    # 1. Seslendirme
    generate_voiceover(template_data['script_body'], mp3_path)
    audio = AudioFileClip(mp3_path)
    audio_duration = audio.duration
    print(f"[+] Ses Suresi: {audio_duration:.2f} saniye")

    # 2. Arka Plan Videosu (Indirme veya Prosedurel Hizli Gorsel)
    bg_url = STOCK_VIDEO_URLS[index % len(STOCK_VIDEO_URLS)]
    downloaded_file = download_bg_video(bg_url, bg_video_path)

    bg_clip = None
    if downloaded_file and os.path.exists(downloaded_file):
        try:
            raw_clip = VideoFileClip(downloaded_file)
            if raw_clip.duration < audio_duration:
                sub_d = min(raw_clip.duration, audio_duration)
                bg_clip = raw_clip.subclipped(0, sub_d)
            else:
                bg_clip = raw_clip.subclipped(0, audio_duration)

            w, h = bg_clip.size
            target_w, target_h = 1080, 1920
            scale_ratio = max(target_w / w, target_h / h)
            bg_clip = bg_clip.resized(scale_ratio)
            
            w_new, h_new = bg_clip.size
            x_center = (w_new - target_w) / 2
            y_center = (h_new - target_h) / 2
            bg_clip = bg_clip.cropped(x1=x_center, y1=y_center, width=target_w, height=target_h)
            bg_clip = bg_clip.with_duration(audio_duration)
        except Exception as e:
            print(f"[!] Video dosya okuma uyarisi ({e}), ultra-hizli YZ arka plana geciliyor...")
            bg_clip = None

    if bg_clip is None:
        bg_arr = make_procedural_bg_image(style_index=index)
        bg_clip = ImageClip(bg_arr).with_duration(audio_duration)

    overlay_clips = [bg_clip]

    # Karartma Katmani
    dark_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.30).with_duration(audio_duration)
    overlay_clips.append(dark_overlay)

    # Ust Baslik Banner (Gold Renk)
    title_img = create_text_image(template_data['caption_title'], font_size=64, text_color="#FFD700")
    title_clip = ImageClip(title_img).with_duration(audio_duration).with_position(("center", 180))
    overlay_clips.append(title_clip)

    # Dinamik Altyazi Klipleri
    phrases = split_text_into_phrases(template_data['script_body'], max_words=5)
    phrase_duration = audio_duration / len(phrases)

    for i, phrase in enumerate(phrases):
        start_t = i * phrase_duration
        color = "#FFD700" if i % 2 == 0 else "#FFFFFF"
        sub_img = create_text_image(phrase, font_size=56, text_color=color)
        sub_clip = ImageClip(sub_img).with_start(start_t).with_duration(phrase_duration).with_position(("center", "center"))
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
