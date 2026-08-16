import os
import json
import time
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

# Kanal bazlı SEO tag'leri
NICHE_TAGS = {
    "stoic": ["stoicism", "stoic", "mindset", "discipline", "marcus aurelius", "shorts", "motivation", "viral", "philosophy", "mental strength"],
    "bible": ["bible", "faith", "god", "prayer", "catholic", "christian", "scripture", "shorts", "devotional", "jesus", "spiritual"],
    "health": ["keto", "weightloss", "health", "diet", "fitness", "intermittent fasting", "fat loss", "shorts", "nutrition", "metabolism"],
    "kids":  ["bedtime stories", "kids", "fairy tales", "children", "storytime", "shorts", "animation", "toddler", "nursery", "educational"]
}

# Kanal bazlı description hashtag'leri
NICHE_HASHTAGS = {
    "stoic":  "#stoicism #mindset #discipline #motivation #stoic #mentalstrength #shorts",
    "bible":  "#bible #faith #god #prayer #catholic #christian #scripture #shorts",
    "health": "#keto #weightloss #health #diet #fitness #fatloss #nutrition #shorts",
    "kids":   "#bedtimestories #kids #fairytales #children #storytime #shorts"
}

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"[!] Token yenileme hatası: {e}")
                return None
        else:
            print(f"[!] Geçerli token bulunamadı: {TOKEN_FILE}")
            return None
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_video_and_comment(video_path, metadata, niche_key="stoic"):
    youtube = get_authenticated_service()
    if not youtube:
        print("[!] YouTube API Servisi başlatılamadı.")
        return False

    tags = NICHE_TAGS.get(niche_key, NICHE_TAGS["stoic"])
    hashtags = NICHE_HASHTAGS.get(niche_key, NICHE_HASHTAGS["stoic"])
    description = f"{metadata.get('description', '')}\n\n{hashtags}"

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": description,
            "tags": tags,
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"[+] Video YouTube'a Otomatik Yükleniyor: {metadata['title']}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   [>] Yükleme İlerlemesi: %{int(status.progress() * 100)}")

    video_id = response.get("id")
    print(f"✅ Video Başarıyla Yayınlandı! Video ID: {video_id}")
    print(f"   https://www.youtube.com/shorts/{video_id}")

    # Pinned affiliate comment
    if "pinned_comment" in metadata and video_id:
        try:
            print("[+] Affiliate Linki Yorum Olarak Ekleniyor...")
            comment_body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": metadata["pinned_comment"]
                        }
                    }
                }
            }
            comment_resp = youtube.commentThreads().insert(
                part="snippet", body=comment_body
            ).execute()
            print("✅ Affiliate Linki Yorumu Eklendi!")
        except Exception as e:
            print(f"[!] Yorum ekleme uyarısı: {e}")

    return video_id if video_id else True

if __name__ == "__main__":
    print("YouTube Auto-Uploader Module Ready.")
