import os
import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
VIDEO_ASSETS_DIR = os.path.join(ASSETS_DIR, "moving_videos")
os.makedirs(VIDEO_ASSETS_DIR, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}

# High quality reliable MP4 video clips
FREE_VIDEO_SOURCES = {
    "stoic": [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"
    ],
    "bible": [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4"
    ],
    "health": [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreet.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4"
    ],
    "kids": [
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
    ]
}

def ensure_niche_moving_videos():
    print("[+] Niş Hareketli Stok Videoları Kontrol Ediliyor...")
    for niche, urls in FREE_VIDEO_SOURCES.items():
        for i, url in enumerate(urls):
            video_path = os.path.join(VIDEO_ASSETS_DIR, f"{niche}_video_{i}.mp4")
            if not os.path.exists(video_path) or os.path.getsize(video_path) < 100000:
                try:
                    resp = requests.get(url, headers=headers, stream=True, timeout=30)
                    if resp.status_code == 200:
                        with open(video_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)
                        print(f"✅ {niche.upper()} Video #{i+1} İndirildi: {video_path}")
                except Exception as e:
                    print(f"❌ Video İndirme Uyarısı ({niche}): {e}")

if __name__ == "__main__":
    ensure_niche_moving_videos()
