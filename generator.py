import sys
import io
import os
import json
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, ColorClip, concatenate_videoclips
from ai_script_generator import generate_ai_topic_and_script
from pexels_downloader import download_two_pexels_videos

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

NICHE_VOICES = {
    "stoic":  "en-US-ChristopherNeural",
    "bible":  "en-US-GuyNeural",
    "health": "en-US-JennyNeural",
    "kids":   "en-US-AnaNeural"
}

def generate_voiceover_with_sync(text, voice_path, voice_name="en-US-ChristopherNeural"):
    print(f"[+] TTS Seslendirme: {voice_name}")
    sentence_boundaries = []

    async def amake():
        communicate = edge_tts.Communicate(text, voice_name)
        with open(voice_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    sentence_boundaries.append({
                        "text": chunk["text"],
                        "start": chunk["offset"] / 10_000_000.0,
                        "duration": chunk["duration"] / 10_000_000.0
                    })

    asyncio.run(amake())
    return sentence_boundaries

def create_text_image(text, max_width=960, font_size=72, text_color="#FFFF00", bg_color=(0, 0, 0, 210), stroke_color="black"):
    font = None
    custom_font_path = os.path.join(ASSETS_DIR, "font.ttf")
    if os.path.exists(custom_font_path):
        try:
            font = ImageFont.truetype(custom_font_path, font_size)
        except Exception:
            pass
    if font is None:
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
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
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    line_height = font_size + 20
    max_line_w = max((draw.textbbox((0,0), l, font=font)[2] - draw.textbbox((0,0), l, font=font)[0]) for l in lines) if lines else 100
    pad_x, pad_y = 32, 16
    box_w = max_line_w + pad_x * 2
    box_h = len(lines) * line_height + pad_y * 2

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if bg_color:
        draw.rounded_rectangle([0, 0, box_w, box_h], radius=20, fill=bg_color)

    stroke_w = 5
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lx = (box_w - lw) // 2
        ly = pad_y + i * line_height
        for sx in range(-stroke_w, stroke_w + 1):
            for sy in range(-stroke_w, stroke_w + 1):
                draw.text((lx + sx, ly + sy), line, font=font, fill=stroke_color)
        draw.text((lx, ly), line, font=font, fill=text_color)

    return np.array(img)

def prepare_background_video(bg_video_path, target_duration):
    """
    Pexels videosunu 1080x1920 dikey formata getir.
    Hedef süreye göre döngüye al veya kes.
    """
    clip = VideoFileClip(bg_video_path)
    
    # Dikey formata getir (9:16 crop)
    orig_w, orig_h = clip.size
    target_w, target_h = 1080, 1920
    
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    clip = clip.resized((new_w, new_h))
    
    # Ortadan kırp
    x_center = new_w // 2
    y_center = new_h // 2
    clip = clip.cropped(
        x1=x_center - target_w // 2,
        y1=y_center - target_h // 2,
        x2=x_center + target_w // 2,
        y2=y_center + target_h // 2
    )
    
    # Süreye göre döngüye al veya kes
    if clip.duration < target_duration:
        loops = int(target_duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * loops)
    
    clip = clip.subclipped(0, target_duration)
    return clip

def create_video_from_template(template_data, index, niche_key="stoic"):
    clean_title = template_data['title'].encode('ascii', errors='ignore').decode('ascii')
    print(f"\n==========================================")
    print(f"[+] Video #{index+1} [{niche_key.upper()}]: {clean_title}")
    print(f"==========================================")

    voice_name = NICHE_VOICES.get(niche_key, "en-US-ChristopherNeural")
    video_id = f"video_{index+1}_{template_data['id']}"
    mp3_path = os.path.join(ASSETS_DIR, f"{video_id}.mp3")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")

    # 1. TTS Seslendirme
    sentence_boundaries = generate_voiceover_with_sync(template_data['script_body'], mp3_path, voice_name)
    voice_audio = AudioFileClip(mp3_path)
    audio_duration = voice_audio.duration
    print(f"[+] Ses Suresi: {audio_duration:.2f}s")

    # 2. Pexels'ten 2 FARKLI Gerçek Hareketli Video İndir ve Birleştir
    video_search_query = template_data.get('video_search_query', None)
    print(f"[+] 2 Pexels videosu aranıyor...")
    bg_videos, total_bg_dur = download_two_pexels_videos(
        niche_key,
        custom_query=video_search_query
    )

    overlay_clips = []

    if bg_videos:
        # Her videoyu 1080x1920'ye getir ve birleştir
        processed = []
        for bg_path, bg_dur in bg_videos:
            try:
                clip = VideoFileClip(bg_path)
                orig_w, orig_h = clip.size
                scale = max(1080 / orig_w, 1920 / orig_h)
                clip = clip.resized((int(orig_w * scale), int(orig_h * scale)))
                x_c, y_c = clip.size[0] // 2, clip.size[1] // 2
                clip = clip.cropped(x1=x_c-540, y1=y_c-960, x2=x_c+540, y2=y_c+960)
                processed.append(clip)
            except Exception as e:
                print(f"[!] Video crop hatası: {e}")

        if processed:
            # Birleştir ve hedef süreye getir
            combined = concatenate_videoclips(processed, method="compose")
            if combined.duration < audio_duration:
                # Yeterli değilse döngüye al
                loops = int(audio_duration / combined.duration) + 1
                combined = concatenate_videoclips([combined] * loops, method="compose")
            bg_clip = combined.subclipped(0, audio_duration)
            overlay_clips.append(bg_clip)
            print(f"✅ Arka plan hazır: {audio_duration:.1f}s ({len(processed)} video birleştirildi)")
        else:
            bg_clip = ColorClip(size=(1080, 1920), color=(10, 10, 10)).with_duration(audio_duration)
            overlay_clips.append(bg_clip)
    else:
        print(f"[!] Pexels video bulunamadı, siyah arka plan")
        bg_clip = ColorClip(size=(1080, 1920), color=(10, 10, 10)).with_duration(audio_duration)
        overlay_clips.append(bg_clip)

    # 3. Karartma overlay (%35 opacity)
    dark = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.35).with_duration(audio_duration)
    overlay_clips.append(dark)

    # 4. Üst başlık banner
    title_img = create_text_image(template_data['caption_title'], font_size=68, text_color="#FFD700", bg_color=(0,0,0,220))
    title_clip = ImageClip(title_img).with_duration(audio_duration).with_position(("center", 160))
    overlay_clips.append(title_clip)

    # 5. Senkronize altyazılar
    color_palette = ["#FFFF00", "#00FF88", "#FFFFFF", "#FFD700", "#FF6B6B"]
    phrase_count = 0
    if sentence_boundaries:
        for sb in sentence_boundaries:
            words = sb["text"].split()
            chunks = [" ".join(words[k:k+3]) for k in range(0, len(words), 3)]
            chunk_dur = sb["duration"] / max(1, len(chunks))
            for k, chunk in enumerate(chunks):
                phrase_start = sb["start"] + k * chunk_dur
                color = color_palette[phrase_count % len(color_palette)]
                phrase_count += 1
                sub_img = create_text_image(chunk, font_size=72, text_color=color)
                sub_clip = ImageClip(sub_img).with_start(phrase_start).with_duration(chunk_dur).with_position(("center", 1180))
                overlay_clips.append(sub_clip)

    # 6. Birleştir ve Render Et
    final_video = CompositeVideoClip(overlay_clips).with_audio(voice_audio).with_duration(audio_duration)
    print(f"[+] MP4 Render: {output_mp4}")
    final_video.write_videofile(
        output_mp4,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=4,
        logger=None
    )
    final_video.close()
    voice_audio.close()

    # MP3 temizle
    try:
        os.remove(mp3_path)
    except Exception:
        pass

    return output_mp4

def main(niche_key="stoic"):
    print(f"[+] PEXELS VIDEO SHORTS FABRIKASI [{niche_key.upper()}]")
    templates_path = os.path.join(BASE_DIR, "templates.json")
    with open(templates_path, "r", encoding="utf-8") as f:
        templates = json.load(f)

    generated = []
    for i, tmpl in enumerate(templates[:3]):
        try:
            path = create_video_from_template(tmpl, i, niche_key=niche_key)
            generated.append(path)
        except Exception as e:
            print(f"[!] Video {i+1} hatasi: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ {len(generated)}/{len(templates[:3])} video uretildi:")
    for g in generated:
        print(f"  - {g}")

if __name__ == "__main__":
    main()
