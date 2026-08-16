import os
import sys
import io
import json
import shutil
import random

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

import generator
import youtube_uploader
import ai_script_generator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
HISTORY_FILE = os.path.join(BASE_DIR, "posted_history.json")

CHANNELS = [
    {
        "niche": "stoic",
        "name": "Obsidian Stoic (Motivation)",
        "token": "token.json",
        "secrets": "client_secrets.json"
    },
    {
        "niche": "bible",
        "name": "Sacred Word Bible (Catholic/Bible)",
        "token": "token_bible.json",
        "secrets": "client_secrets_bible.json"
    },
    {
        "niche": "health",
        "name": "VitalityDailyHealth (Health/Diet)",
        "token": "token_health.json",
        "secrets": "client_secrets_health.json"
    },
    {
        "niche": "kids",
        "name": "BedtimeStoriesMagicc (Kids Stories)",
        "token": "token_kids.json",
        "secrets": "client_secrets_kids.json"
    }
]

print("====================================================")
print("🚀 4 KANAL İÇİN DİJİTAL YZ SHORTS FABRİKASI BAŞLATILIYOR")
print("====================================================\n")

# Load history tracker
posted_history = {}
if os.path.exists(HISTORY_FILE):
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            posted_history = json.load(f)
    except Exception:
        posted_history = {}

for ch in CHANNELS:
    niche_key = ch['niche']
    print("\n====================================================")
    print(f"[+] KANAL İŞLENİYOR: {ch['name']}")
    print("====================================================")

    token_src = os.path.join(BASE_DIR, ch['token'])
    token_dst = os.path.join(BASE_DIR, "token.json")

    secrets_src = os.path.join(BASE_DIR, ch['secrets'])
    secrets_dst = os.path.join(BASE_DIR, "client_secrets.json")

    if not os.path.exists(token_src) or not os.path.exists(secrets_src):
        print(f"[!] İzin dosyaları bulunamadı, bu kanal atlanıyor: {ch['name']}")
        continue

    posted_ids = posted_history.get(niche_key, [])

    # 1. Gemini Yapay Zekası İle %100 Benzersiz 3 Yeni Konu + FLUX Promptu Üret
    print(f"[+] Gemini Yapay Zekası {ch['name']} İçin 3 YEPYENİ Konu ve FLUX Görsel Komutları Hazırlıyor...")
    selected_templates = []
    for _ in range(3):
        try:
            ai_data = ai_script_generator.generate_ai_topic_and_script(niche_key=niche_key, posted_history=posted_ids)
            if ai_data:
                selected_templates.append(ai_data)
        except Exception as e:
            print(f"[!] AI Konu Üretim Uyarısı: {e}")

    if not selected_templates:
        print(f"[!] YZ senaryo üretemedi, bu kanal atlanıyor.")
        continue

    # Write selected 3 templates to active templates.json
    templates_dst = os.path.join(BASE_DIR, "templates.json")
    with open(templates_dst, "w", encoding="utf-8") as f:
        json.dump(selected_templates, f, indent=2, ensure_ascii=False)

    # Swap credential files safely
    if os.path.abspath(token_src) != os.path.abspath(token_dst):
        shutil.copyfile(token_src, token_dst)
    if os.path.abspath(secrets_src) != os.path.abspath(secrets_dst):
        shutil.copyfile(secrets_src, secrets_dst)

    # 2. Video Üretimi (FLUX 8K AI Görselleri + Milisaniye Ses Altyazı Senkronu)
    print(f"[+] {ch['name']} için 3 Benzersiz YZ Görselli Video Render Ediliyor...")
    try:
        generator.main(niche_key=niche_key)
    except Exception as e:
        print(f"[!] Video üretim hatası ({ch['name']}): {e}")

    # 3. Otomatik YouTube Yükleme & Dolar Linki Yorum Sabitleme
    print(f"[+] {ch['name']} YouTube Kanalına Yükleme Yapılıyor...")
    try:
        for i, t in enumerate(selected_templates):
            video_id = f"video_{i+1}_{t['id']}"
            video_path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
            
            metadata = {
                "title": t["title"],
                "description": f"{t['script_body']}\n\n#shorts #viral",
                "pinned_comment": t["pinned_comment"]
            }

            if os.path.exists(video_path):
                success = youtube_uploader.upload_video_and_comment(video_path, metadata)
                if success:
                    posted_ids.append(t["id"])
                    posted_ids.append(t["title"])
    except Exception as e:
        print(f"[!] YouTube Yükleme hatası ({ch['name']}): {e}")

    # Save updated posted history
    posted_history[niche_key] = posted_ids

# Save history file
with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(posted_history, f, indent=2, ensure_ascii=False)

print("\n====================================================")
print("🎉 TEBRİKLER! 4 KANALIN TÜM YZ GÖRSELLİ BENZERSİZ VİDEOLARI ÜRETİLDİ VE YÜKLENDİ!")
print("====================================================")
