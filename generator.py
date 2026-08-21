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

from moviepy import (
    VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip,
    ColorClip, CompositeAudioClip, concatenate_videoclips, vfx
)
from ai_script_generator import generate_ai_topic_and_script
from pexels_downloader import download_segment_videos
from download_bg_music import ensure_bgm_files

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
BGM_DIR = os.path.join(ASSETS_DIR, "bg_music")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(BGM_DIR, exist_ok=True)

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

def create_highlighted_subtitle_image(words, active_index, max_width=960, font_size=72):
    """
    Kelime Kelime Vurgulu Altyazı Görseli (Word Highlight Kinetic Subtitles)
    Aktif kelime parlak sarı/altın, diğer kelimeler temiz beyaz renkte render edilir.
    """
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

    # Line wrapping logic
    lines = []
    current_line = []
    for w_obj in words:
        current_line.append(w_obj)
        test_text = " ".join(item["word"].upper() for item in current_line)
        bbox = draw.textbbox((0, 0), test_text, font=font)
        if (bbox[2] - bbox[0]) > max_width:
            current_line.pop()
            if current_line:
                lines.append(current_line)
            current_line = [w_obj]
    if current_line:
        lines.append(current_line)

    line_height = font_size + 24
    max_line_w = 0
    for line in lines:
        l_text = " ".join(item["word"].upper() for item in line)
        bbox = draw.textbbox((0, 0), l_text, font=font)
        w = bbox[2] - bbox[0]
        if w > max_line_w:
            max_line_w = w

    pad_x, pad_y = 36, 20
    box_w = max_line_w + pad_x * 2
    box_h = len(lines) * line_height + pad_y * 2

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark rounded background box with 85% opacity
    draw.rounded_rectangle([0, 0, box_w, box_h], radius=24, fill=(0, 0, 0, 215))

    word_counter = 0
    stroke_w = 5

    for i, line in enumerate(lines):
        # Calculate full line width to center it horizontally
        full_line_text = " ".join(item["word"].upper() for item in line)
        line_bbox = draw.textbbox((0, 0), full_line_text, font=font)
        line_w = line_bbox[2] - line_bbox[0]
        start_x = (box_w - line_w) // 2
        curr_x = start_x
        curr_y = pad_y + i * line_height

        for item in line:
            w_str = item["word"].upper()
            w_bbox = draw.textbbox((0, 0), w_str, font=font)
            w_width = w_bbox[2] - w_bbox[0]

            is_active = (word_counter == active_index)
            color = "#FFFF00" if is_active else "#FFFFFF"  # Active: Neon Yellow, Normal: White
            stroke_color = "#000000"

            # Draw text stroke
            for sx in range(-stroke_w, stroke_w + 1):
                for sy in range(-stroke_w, stroke_w + 1):
                    draw.text((curr_x + sx, curr_y + sy), w_str, font=font, fill=stroke_color)

            # Draw word
            draw.text((curr_x, curr_y), w_str, font=font, fill=color)

            space_w = draw.textbbox((0, 0), " ", font=font)[2]
            curr_x += w_width + space_w
            word_counter += 1

    return np.array(img)

def prepare_multi_clip_background(segment_clips_paths, audio_duration):
    """
    Cümle Bazlı Çoklu Stok Video Değişimi + Crossfade Yumuşak Geçişler
    4-5 farklı Pexels videosunu kesip yumuşak geçişlerle (Crossfade) birleştirir.
    """
    if not segment_clips_paths:
        return ColorClip(size=(1080, 1920), color=(10, 10, 10)).with_duration(audio_duration)

    num_clips = len(segment_clips_paths)
    per_clip_duration = (audio_duration / num_clips) + 0.4  # Slight overlap for crossfade

    processed_clips = []
    for path, dur in segment_clips_paths:
        try:
            clip = VideoFileClip(path)
            orig_w, orig_h = clip.size
            scale = max(1080 / orig_w, 1920 / orig_h)
            clip = clip.resized((int(orig_w * scale), int(orig_h * scale)))
            x_c, y_c = clip.size[0] // 2, clip.size[1] // 2
            clip = clip.cropped(x1=x_c - 540, y1=y_c - 960, x2=x_c + 540, y2=y_c + 960)

            # Loop if clip is too short
            if clip.duration < per_clip_duration:
                loops = int(per_clip_duration / clip.duration) + 1
                clip = concatenate_videoclips([clip] * loops)

            clip = clip.subclipped(0, min(per_clip_duration, clip.duration))
            # Crossfade in transition (MoviePy 2.0 syntax)
            clip = clip.with_effects([vfx.CrossFadeIn(0.3)])
            processed_clips.append(clip)
        except Exception as e:
            print(f"[!] Clip process error: {e}")

    if not processed_clips:
        return ColorClip(size=(1080, 1920), color=(10, 10, 10)).with_duration(audio_duration)

    # Stitch clips with crossfade padding
    combined = concatenate_videoclips(processed_clips, method="compose", padding=-0.3)
    if combined.duration < audio_duration:
        loops = int(audio_duration / combined.duration) + 1
        combined = concatenate_videoclips([combined] * loops, method="compose")

    return combined.subclipped(0, audio_duration)

def create_video_from_template(template_data, index, niche_key="stoic"):
    clean_title = template_data['title'].encode('ascii', errors='ignore').decode('ascii')
    print(f"\n==========================================")
    print(f"[+] Video #{index+1} [{niche_key.upper()}]: {clean_title}")
    print(f"==========================================")

    voice_name = NICHE_VOICES.get(niche_key, "en-US-ChristopherNeural")
    video_id = f"video_{index+1}_{template_data['id']}"
    mp3_path = os.path.join(ASSETS_DIR, f"{video_id}.mp3")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")

    # 1. TTS Voiceover & Sentence Boundaries
    sentence_boundaries = generate_voiceover_with_sync(template_data['script_body'], mp3_path, voice_name)
    voice_audio = AudioFileClip(mp3_path)
    audio_duration = voice_audio.duration
    
    # KESİN SHORTS LİMİTİ: Video süresi 54.0 saniyeyi asla geçemez!
    if audio_duration > 54.0:
        print(f"⚠️ Ses süresi ({audio_duration:.2f}s) 54s limitini aşıyor, 54.0s'ye kırpılıp yumuşak fade-out yapılıyor!")
        audio_duration = 54.0
        voice_audio = voice_audio.subclipped(0, 54.0)

    print(f"[+] Final Ses Suresi: {audio_duration:.2f}s")

    # 2. Arka Plan Fon Müziği (BGM Auto-Mixer %14 Volume)
    ensure_bgm_files()
    bgm_path = os.path.join(BGM_DIR, f"{niche_key}_bg_music.mp3")
    final_audio = voice_audio

    if os.path.exists(bgm_path):
        try:
            bgm_raw = AudioFileClip(bgm_path)
            if bgm_raw.duration < audio_duration:
                loops = int(audio_duration / bgm_raw.duration) + 1
                bgm_raw = concatenate_videoclips([bgm_raw] * loops)
            bgm_clip = bgm_raw.subclipped(0, audio_duration).with_volume_scaled(0.14)
            final_audio = CompositeAudioClip([voice_audio, bgm_clip])
            print(f"✅ CC0 Arka Plan Fon Müziği Karıştırıldı (%14 Ses Seviyesi)")
        except Exception as e:
            print(f"[!] BGM Mix uyarısı: {e}")

    # 3. Cümle Bazlı 4 Farklı Pexels Stok Videosu İndir
    queries = [template_data.get('video_search_query', None)]
    queries += [f"{niche_key} dramatic landscape", f"{niche_key} powerful scene", f"{niche_key} atmosphere"]
    segment_clips = download_segment_videos(niche_key, segment_queries=queries, target_count=4)

    overlay_clips = []

    # 4. Multi-Clip Background & Crossfade Transitions
    bg_video_clip = prepare_multi_clip_background(segment_clips, audio_duration)
    overlay_clips.append(bg_video_clip)

    # 5. Sinematik Karartma Katmanı (%35 Opacity)
    dark_overlay = ColorClip(size=(1080, 1920), color=(0, 0, 0)).with_opacity(0.35).with_duration(audio_duration)
    overlay_clips.append(dark_overlay)

    # 6. Üst Başlık Banner (Top Center y=160)
    title_img = create_highlighted_subtitle_image(
        [{"word": w} for w in template_data['caption_title'].split()],
        active_index=-1,
        font_size=68
    )
    title_clip = ImageClip(title_img).with_duration(audio_duration).with_position(("center", 160))
    overlay_clips.append(title_clip)

    # 7. Kelime Vurgulu Kinetik Altyazılar (Word Highlight Subtitles)
    if sentence_boundaries:
        for sb in sentence_boundaries:
            s_text = sb["text"]
            s_start = sb["start"]
            s_dur = sb["duration"]
            raw_words = s_text.split()
            if not raw_words:
                continue

            # Break long sentences into 3-4 word phrases for screen readability
            chunks = [raw_words[k:k+4] for k in range(0, len(raw_words), 4)]
            chunk_dur = s_dur / len(chunks)

            for c_idx, chunk in enumerate(chunks):
                phrase_start = s_start + (c_idx * chunk_dur)
                word_objs = [{"word": w} for w in chunk]
                word_dur = chunk_dur / len(word_objs)

                # Generate highlighted text frames per word
                for w_idx in range(len(word_objs)):
                    w_frame_start = phrase_start + (w_idx * word_dur)
                    img_np = create_highlighted_subtitle_image(word_objs, active_index=w_idx, font_size=72)
                    sub_clip = (
                        ImageClip(img_np)
                        .with_start(w_frame_start)
                        .with_duration(word_dur)
                        .with_position(("center", 1180))
                    )
                    overlay_clips.append(sub_clip)

    # 8. Birleştirme ve MP4 Render
    final_video = CompositeVideoClip(overlay_clips).with_audio(final_audio).with_duration(audio_duration)
    print(f"[+] MP4 Render Ediliyor -> {output_mp4}")
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

    try:
        os.remove(mp3_path)
    except Exception:
        pass

    return output_mp4

def main(niche_key="stoic"):
    print(f"[+] MONEYPRINTER TURBO PLUS VİDEO MOTORU [{niche_key.upper()}]")
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
