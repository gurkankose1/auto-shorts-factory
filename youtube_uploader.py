import os
import json
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
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

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"[!] HATA: {CLIENT_SECRETS_FILE} bulunamadı.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

def upload_video_and_comment(video_path, metadata):
    youtube = get_authenticated_service()
    if not youtube:
        print("[!] YouTube API Servisi başlatılamadı.")
        return False

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": ["stoicism", "mindset", "shorts", "motivation", "viral"],
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

    # Auto-post Pinned Comment
    if "pinned_comment" in metadata and video_id:
        try:
            print("[+] Dolar Affiliate Linki Yorum Olarak Sabitleniyor...")
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
            youtube.commentThreads().insert(part="snippet", body=comment_body).execute()
            print("✅ Dolar Linkli Yorum Başarıyla Sabitlendi!")
        except Exception as e:
            print(f"[!] Yorum ekleme uyarısı: {e}")

    return True

if __name__ == "__main__":
    print("YouTube Auto-Uploader Module Ready.")
