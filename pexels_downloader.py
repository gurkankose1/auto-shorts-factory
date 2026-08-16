import requests
import os
import sys
import json
import random
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "scYOaItPyRN4xvhe7T1eIz4Ofo4bNBsMQiQvNB4JDugi07KdPjeBGUsR")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
VIDEO_CACHE_FILE = os.path.join(BASE_DIR, "used_pexels_videos.json")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Her niş için çok sayıda arama terimi — maksimum çeşitlilik
NICHE_QUERIES = {
    "stoic": [
        "mountain dramatic sunrise", "dark forest silhouette", "ocean waves storm dramatic",
        "fire flames dark background", "misty mountain landscape", "person silhouette sunset",
        "night sky stars milky way", "rain window dark moody", "eagle flying freedom",
        "waterfall nature dramatic", "thunderstorm lightning", "lone tree field sunset",
        "smoke dark abstract", "wolf nature wild", "rocky cliff ocean",
        "dark clouds dramatic sky", "sunrise mountain peak", "ancient stone ruins",
        "river flowing nature", "fog forest mysterious"
    ],
    "bible": [
        "church light rays", "sunset clouds heaven", "candle light dark prayer",
        "cross silhouette sunrise", "nature peaceful meadow", "dove flying sky",
        "golden hour light landscape", "misty valley morning", "water reflection calm",
        "wheat field breeze", "lighthouse ocean hope", "rainbow after storm",
        "forest light rays", "sunrise horizon golden", "cathedral interior light",
        "mountain cross", "peaceful lake sunrise", "holy light nature",
        "stars night sky peaceful", "flowing river serene"
    ],
    "health": [
        "healthy food vegetables fresh", "running fitness motivation", "gym workout training",
        "fresh fruit morning breakfast", "nature walk green", "green smoothie healthy",
        "yoga meditation morning", "salad fresh vegetables", "water splash fresh",
        "sunrise run jogging", "avocado healthy food", "kitchen cooking fresh",
        "jumping fitness energy", "beach workout fitness", "cycling outdoor sport",
        "vegetables market fresh", "athletic training outdoor", "healthy lifestyle morning",
        "swimming fitness", "hiking nature trail"
    ],
    "kids": [
        "stars night sky magical", "magical forest fairy", "colorful flowers nature",
        "sunset peaceful golden", "butterfly garden", "rainbow colorful sky",
        "fireflies night magical", "meadow flowers spring", "ocean waves calm blue",
        "snow winter magical", "autumn leaves falling", "waterfall tropical green",
        "clouds timelapse sky", "night moon stars", "hot air balloon sky",
        "colorful birds nature", "mushroom forest magical", "kite flying sky",
        "dandelion wind blowing", "cherry blossom spring"
    ]
}

def load_used_videos():
    if os.path.exists(VIDEO_CACHE_FILE):
        try:
            with open(VIDEO_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_used_videos(used):
    with open(VIDEO_CACHE_FILE, "w") as f:
        json.dump(used, f, indent=2)

def fetch_pexels_videos(query, per_page=15):
    headers = {"Authorization": PEXELS_API_KEY}
    page = random.randint(1, 3)
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "portrait",
        "size": "medium",
        "page": page
    }
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get("videos", [])
    except Exception as e:
        print(f"[!] Pexels fetch error: {e}")
    return []

def get_best_video_file(video):
    files = video.get("video_files", [])
    portrait_files = [f for f in files if f.get("height", 0) >= f.get("width", 1)]
    if not portrait_files:
        portrait_files = files
    hd = [f for f in portrait_files if f.get("quality") == "hd"]
    sd = [f for f in portrait_files if f.get("quality") == "sd"]
    candidates = hd if hd else sd
    if not candidates:
        return None
    return sorted(candidates, key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)[0]

def download_single_video(niche_key, custom_query=None, min_duration=8, max_duration=60, exclude_ids=None):
    """Tek bir Pexels videosu indir — daha önce kullanılanları atla"""
    used = load_used_videos()
    used_ids = set(used.get(niche_key, []))
    if exclude_ids:
        used_ids.update(exclude_ids)

    queries = []
    if custom_query:
        queries.append(custom_query)
    niche_q = NICHE_QUERIES.get(niche_key, NICHE_QUERIES["stoic"])[:]
    random.shuffle(niche_q)
    queries += niche_q

    for query in queries:
        print(f"   [Pexels] Aranıyor: '{query}'")
        videos = fetch_pexels_videos(query)

        suitable = []
        short_candidates = []
        for v in videos:
            vid_id = str(v["id"])
            duration = v.get("duration", 0)
            if vid_id in used_ids:
                continue
            best_file = get_best_video_file(v)
            if not best_file:
                continue
            if min_duration <= duration <= max_duration:
                suitable.append((v, best_file))
            elif duration >= 8:
                short_candidates.append((v, best_file))

        candidates = suitable if suitable else short_candidates
        if not candidates:
            continue

        chosen_video, chosen_file = random.choice(candidates)
        vid_id = str(chosen_video["id"])
        duration = chosen_video["duration"]
        video_url = chosen_file["link"]

        print(f"   ✅ Seçildi: ID={vid_id} | {duration}s | {chosen_file.get('width')}x{chosen_file.get('height')}")

        output_path = os.path.join(ASSETS_DIR, f"bg_{niche_key}_{vid_id}.mp4")

        if not os.path.exists(output_path):
            try:
                r = requests.get(video_url, stream=True, timeout=90)
                if r.status_code == 200:
                    with open(output_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=16384):
                            f.write(chunk)
                    print(f"   ✅ İndirildi: {output_path}")
                else:
                    print(f"   ❌ İndirme hatası: {r.status_code}")
                    continue
            except Exception as e:
                print(f"   ❌ İndirme exception: {e}")
                continue
        else:
            print(f"   [+] Cache'den kullanılıyor: {output_path}")

        # ID kaydet
        if niche_key not in used:
            used[niche_key] = []
        if vid_id not in used[niche_key]:
            used[niche_key].append(vid_id)
        if len(used[niche_key]) > 100:
            used[niche_key] = used[niche_key][-100:]
        save_used_videos(used)

        return output_path, duration, vid_id

    return None, 0, None


def download_two_pexels_videos(niche_key, custom_query=None):
    """
    2 FARKLI video indir — birleştirilince 25-40 saniyelik arka plan garantisi.
    İkinci video farklı bir sorgudan gelir.
    """
    print(f"[+] {niche_key.upper()} için 2 Pexels videosu aranıyor...")

    # 1. Video
    path1, dur1, id1 = download_single_video(
        niche_key,
        custom_query=custom_query,
        min_duration=8,
        max_duration=40
    )

    # 2. Video — farklı ID olsun
    exclude = {id1} if id1 else set()
    path2, dur2, id2 = download_single_video(
        niche_key,
        custom_query=None,  # Farklı sorgu için custom_query kullanma
        min_duration=8,
        max_duration=40,
        exclude_ids=exclude
    )

    results = []
    total = 0
    if path1:
        results.append((path1, dur1))
        total += dur1
    if path2:
        results.append((path2, dur2))
        total += dur2

    print(f"[+] Toplam arka plan süresi: {total:.1f}s ({len(results)} video)")
    return results, total


if __name__ == "__main__":
    print("=== Pexels 2-Video Download Test ===")
    for niche in ["stoic", "bible", "health", "kids"]:
        print(f"\n[TEST] {niche.upper()}")
        videos, total = download_two_pexels_videos(niche)
        for path, dur in videos:
            print(f"  ✅ {path} ({dur}s)")
        print(f"  Toplam: {total}s")
