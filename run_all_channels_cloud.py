import os
import sys
import io
import json
import shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import generator
import youtube_uploader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")

CHANNELS = [
    {
        "niche": "stoic",
        "name": "Obsidian Stoic (Motivation)",
        "templates": "templates.json",
        "token": "token.json",
        "secrets": "client_secrets.json"
    },
    {
        "niche": "bible",
        "name": "Sacred Word Bible (Catholic/Bible)",
        "templates": "templates_bible.json",
        "token": "token_bible.json",
        "secrets": "client_secrets_bible.json"
    },
    {
        "niche": "health",
        "name": "VitalityDailyHealth (Health/Diet)",
        "templates": "templates_health.json",
        "token": "token_health.json",
        "secrets": "client_secrets_health.json"
    },
    {
        "niche": "kids",
        "name": "BedtimeStoriesMagicc (Kids Stories)",
        "templates": "templates_kids.json",
        "token": "token_kids.json",
        "secrets": "client_secrets_kids.json"
    }
]

print("====================================================")
print("🚀 4 KANAL İÇİN DİJİTAL SHORTS FABRİKASI BAŞLATILIYOR")
print("====================================================\n")

for ch in CHANNELS:
    print(f"\n====================================================")
    print(f"[+] KANAL İŞLENİYOR: {ch['name']}")
    print(f"====================================================")

    templates_src = os.path.join(BASE_DIR, ch['templates'])
    templates_dst = os.path.join(BASE_DIR, "templates.json")

    token_src = os.path.join(BASE_DIR, ch['token'])
    token_dst = os.path.join(BASE_DIR, "token.json")

    secrets_src = os.path.join(BASE_DIR, ch['secrets'])
    secrets_dst = os.path.join(BASE_DIR, "client_secrets.json")

    if not os.path.exists(token_src) or not os.path.exists(secrets_src):
        print(f"[!] İzin dosyaları bulunamadı, bu kanal atlanıyor: {ch['name']}")
        continue

    # Swap config files for current channel safely
    if os.path.abspath(templates_src) != os.path.abspath(templates_dst):
        shutil.copyfile(templates_src, templates_dst)
    if os.path.abspath(token_src) != os.path.abspath(token_dst):
        shutil.copyfile(token_src, token_dst)
    if os.path.abspath(secrets_src) != os.path.abspath(secrets_dst):
        shutil.copyfile(secrets_src, secrets_dst)

    # 1. Video Üretimi (Nişe özel ses ve nişe özel HD görseller)
    print(f"[+] {ch['name']} için 3 Video Render Ediliyor...")
    try:
        generator.main(niche_key=ch['niche'])
    except Exception as e:
        print(f"[!] Video üretim hatası ({ch['name']}): {e}")

    # 2. Otomatik YouTube Yükleme & Yorum Sabitleme
    print(f"[+] {ch['name']} YouTube Kanalına Yükleme Yapılıyor...")
    try:
        with open(os.path.join(BASE_DIR, "templates.json"), "r", encoding="utf-8") as f:
            templates = json.load(f)

        for i, t in enumerate(templates[:3]):
            video_id = f"video_{i+1}_{t['id']}"
            video_path = os.path.join(OUTPUT_DIR, f"{video_id}.mp4")
            
            metadata = {
                "title": t["title"],
                "description": f"{t['script_body']}\n\n#shorts #viral",
                "pinned_comment": t["pinned_comment"]
            }

            if os.path.exists(video_path):
                youtube_uploader.upload_video_and_comment(video_path, metadata)
    except Exception as e:
        print(f"[!] YouTube Yükleme hatası ({ch['name']}): {e}")

print("\n====================================================")
print("🎉 TEBRİKLER! 4 KANALIN TÜM VİDEOLARI ÜRETİLDİ VE YÜKLENDİ!")
print("====================================================")
