import asyncio
import os
import json
import re
import shutil
import urllib.parse
import requests
import yt_dlp
import glob
import base64
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from ShazamAPI import Shazam
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, TPOS, TCON, APIC, TCMP

app = FastAPI(title="Music Suite 2-in-1")

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Downloads from YouTube go here, and Tagger reads from here
INPUT_DIR = os.path.join(BASE_DIR, "Playlist Download")
COMPLETED_DIR = os.path.join(BASE_DIR, "Music Tag Output")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(COMPLETED_DIR, exist_ok=True)

print(f"--- Music Suite initialized ---")
print(f"Monitoring folder: {INPUT_DIR}")
print(f"Saving to folder: {COMPLETED_DIR}")

iTunes_API = "https://itunes.apple.com/lookup"

class SongCandidate(BaseModel):
    id: str
    title: str
    artist: str
    album: str
    release_date: str
    genre: str
    track_number: int
    track_count: int
    disc_number: int
    disc_count: int
    artwork_url: str
    album_artist: str
    is_compilation: bool

class ApplyRequest(BaseModel):
    filename: str
    metadata: SongCandidate
    convert_to_opus: bool = False

# --- DOWNLOADER HELPERS ---
def download_playlist_sync(url: str, format_type: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    playlist_detected = {"sent": False}  # track if we've sent playlist info

    def progress_hook(d):
        info = d.get('info_dict', {})
        
        # Detect playlist info from the first progress event
        if not playlist_detected["sent"]:
            playlist_title = info.get('playlist_title') or info.get('playlist')
            playlist_count = info.get('n_entries') or info.get('playlist_count')
            if playlist_title and playlist_count:
                asyncio.run_coroutine_threadsafe(
                    queue.put({"type": "playlist_info", "title": playlist_title, "count": playlist_count}),
                    loop
                )
                playlist_detected["sent"] = True

        if d['status'] == 'downloading':
            msg = {
                "type": "progress",
                "video_id": info.get('id', 'unknown'),
                "title": info.get('title', 'Unknown Title'),
                "percent": d.get('_percent_str', '').strip(),
                "speed": d.get('_speed_str', '').strip(),
                "eta": d.get('_eta_str', '').strip(),
                "status": "Downloading"
            }
            asyncio.run_coroutine_threadsafe(queue.put(msg), loop)
        elif d['status'] == 'finished':
            msg = {
                "type": "finished",
                "video_id": info.get('id', 'unknown'),
                "title": info.get('title', 'Unknown Title'),
                "status": "Converting..."
            }
            asyncio.run_coroutine_threadsafe(queue.put(msg), loop)

    def postprocessor_hook(d):
        if d['status'] == 'finished' and d['postprocessor'] == 'FFmpegExtractAudio':
            msg = {
                "type": "done",
                "video_id": d.get('info_dict', {}).get('id', 'unknown'),
                "title": d.get('info_dict', {}).get('title', 'Unknown Title'),
                "status": "Completed"
            }
            asyncio.run_coroutine_threadsafe(queue.put(msg), loop)

    class MyLogger:
        def debug(self, msg): pass
        def warning(self, msg): print(f"Warning: {msg}")
        def error(self, msg):
            print(f"Error: {msg}")
            asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "message": msg}), loop)

    # Nuclear Option: Always download as high-quality MP3 first
    codec = 'mp3'
    quality = '320'

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(INPUT_DIR, '%(title)s.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': codec,
            'preferredquality': quality,
        }],
        'progress_hooks': [progress_hook],
        'postprocessor_hooks': [postprocessor_hook],
        'logger': MyLogger(),
        'ignoreerrors': True,
        'quiet': True,
    }

    try:
        # Send an immediate "starting" message so the UI updates right away
        asyncio.run_coroutine_threadsafe(
            queue.put({"type": "status", "message": "Fetching playlist info..."}),
            loop
        )
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Single pass: extract info AND download together (no double scan)
            ydl.download([url])
        asyncio.run_coroutine_threadsafe(queue.put({"type": "all_complete"}), loop)
    except Exception as e:
        asyncio.run_coroutine_threadsafe(queue.put({"type": "error", "message": str(e)}), loop)


# --- TAGGER HELPERS ---
def get_shazam_info(path):
    try:
        with open(path, 'rb') as f:
            content = f.read()
        shazam = Shazam(content)
        recognize_generator = shazam.recognizeSong()
        res = next(recognize_generator)
        if res and len(res) > 1 and 'track' in res[1]:
            track = res[1]['track']
            title = track.get('title')
            artist = track.get('subtitle')
            adam_id = None
            if 'hub' in track and 'actions' in track['hub']:
                for action in track['hub']['actions']:
                    if action.get('type') == 'applemusicplay':
                        adam_id = action.get('id')
                        break
            return artist, title, adam_id
    except: pass
    return None, None, None

def format_itunes_result(res):
    return {
        "id": str(res.get('trackId', res.get('collectionId', 'unknown'))),
        "title": res.get('trackName', 'Unknown Title'),
        "artist": res.get('artistName', 'Unknown Artist'),
        "album": res.get('collectionName', 'Unknown Album'),
        "release_date": res.get('releaseDate', ''),
        "genre": res.get('primaryGenreName', 'Unknown'),
        "track_number": res.get('trackNumber', 0),
        "track_count": res.get('trackCount', 0),
        "disc_number": res.get('discNumber', 0),
        "disc_count": res.get('discCount', 0),
        "artwork_url": res.get('artworkUrl100', '').replace('100x100bb.jpg', '1000x1000bb.jpg'),
        "album_artist": res.get('collectionArtistName', res.get('artistName', '')),
        "is_compilation": res.get('collectionArtistName') == 'Various Artists'
    }

# --- ROUTES ---

@app.get("/")
async def root():
    return FileResponse("index.html")

# Downloader WebSocket
@app.websocket("/ws/download")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        params = json.loads(data)
        url = params.get("url")
        format_type = params.get("format", "mp3") # Always default to mp3
        
        if not url:
            await websocket.send_json({"type": "error", "message": "No URL provided"})
            await websocket.close()
            return
        
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        
        asyncio.create_task(asyncio.to_thread(download_playlist_sync, url, format_type, queue, loop))
        while True:
            msg = await queue.get()
            await websocket.send_json(msg)
            if msg["type"] == "all_complete" or msg["type"] == "error":
                break
    except WebSocketDisconnect: pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        try: await websocket.close()
        except: pass

# Tagger API
@app.get("/api/files")
def list_files():
    try:
        if not os.path.exists(INPUT_DIR):
            print(f"ERROR: INPUT_DIR does not exist: {INPUT_DIR}")
            return []
        all_files = os.listdir(INPUT_DIR)
        valid_files = [f for f in all_files if f.lower().endswith(('.mp3', '.opus'))]
        valid_files.sort(key=lambda x: os.path.getmtime(os.path.join(INPUT_DIR, x)), reverse=True)
        return valid_files
    except Exception as e:
        print(f"Error listing files: {e}")
        return []

@app.get("/api/completed_files")
def list_completed_files():
    try:
        if not os.path.exists(COMPLETED_DIR):
            return []
        all_files = os.listdir(COMPLETED_DIR)
        valid_files = [f for f in all_files if f.lower().endswith(('.mp3', '.opus'))]
        valid_files.sort(key=lambda x: os.path.getmtime(os.path.join(COMPLETED_DIR, x)), reverse=True)
        return valid_files
    except Exception as e:
        print(f"Error listing completed files: {e}")
        return []

@app.get("/api/stream/{filename}")
def stream_file(filename: str):
    path = os.path.join(INPUT_DIR, filename)
    if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    ext = os.path.splitext(filename)[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/ogg"
    return FileResponse(path, media_type=media_type)

@app.get("/api/identify/{filename}")
def identify_song(filename: str):
    path = os.path.join(INPUT_DIR, filename)
    artist, title, adam_id = get_shazam_info(path)
    candidates = []
    if adam_id:
        url = f"{iTunes_API}?id={adam_id}&country=us"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                results = r.json().get('results', [])
                if results: candidates.append(format_itunes_result(results[0]))
        except: pass
    clean_filename = re.sub(r'\.mp3$|\.opus$', '', filename, flags=re.IGNORECASE)
    search_term = f"{artist} {title}" if artist and title else re.sub(r'[^a-zA-Z0-9\s]', ' ', clean_filename)
    search_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(search_term)}&entity=song&limit=5&country=us"
    try:
        r = requests.get(search_url, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results', [])
            for res in results:
                if not any(c['id'] == str(res.get('trackId')) for c in candidates):
                    candidates.append(format_itunes_result(res))
    except: pass
    return {"artist": artist, "title": title, "candidates": candidates}

@app.get("/api/lookup-link")
def lookup_apple_link(url: str):
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    adam_id = None
    if 'i' in qs:
        adam_id = qs['i'][0]
    else:
        parts = parsed.path.split('/')
        if parts:
            last_part = parts[-1]
            if last_part.isdigit():
                adam_id = last_part
                
    if not adam_id:
        raise HTTPException(status_code=400, detail="Could not extract ID from Apple Music link")
        
    api_url = f"{iTunes_API}?id={adam_id}&country=us"
    try:
        r = requests.get(api_url, timeout=10)
        if r.status_code == 200:
            results = r.json().get('results', [])
            if results:
                return format_itunes_result(results[0])
    except Exception as e:
        print(f"Lookup link error: {e}")
        
    raise HTTPException(status_code=404, detail="Song not found on Apple Music")

@app.post("/api/apply")
def apply_tags(req: ApplyRequest):
    path = os.path.join(INPUT_DIR, req.filename)
    if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    
    m = req.metadata
    ext = os.path.splitext(path)[1].lower()
    
    try:
        # STEP 1: Optional Conversion to Opus
        if req.convert_to_opus and ext == ".mp3":
            try:
                opus_path = os.path.join(INPUT_DIR, f"{os.path.splitext(req.filename)[0]}.opus")
                cmd = [
                    "ffmpeg", "-y", "-i", path,
                    "-c:a", "libopus", "-b:a", "128k", "-vbr", "on",
                    "-map", "0:a", # Important: Ogg cannot map video streams like MP3
                    opus_path
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"FFmpeg stderr: {res.stderr}")
                    raise Exception("FFmpeg failed")
                os.remove(path) # Remove original MP3
                path = opus_path
                ext = ".opus"
            except Exception as e:
                print(f"Conversion to Opus failed: {e}")

        # STEP 2: Tag the file
        if ext == ".mp3":
            try: tags = ID3(path)
            except:
                tags = ID3()
                tags.save(path)
                tags = ID3(path)
                
            tags.add(TIT2(encoding=3, text=m.title))
            tags.add(TPE1(encoding=3, text=m.artist))
            tags.add(TPE2(encoding=3, text=m.album_artist))
            tags.add(TALB(encoding=3, text=m.album))
            if m.release_date: tags.add(TDRC(encoding=3, text=m.release_date.split('-')[0]))
            if m.genre: tags.add(TCON(encoding=3, text=m.genre))
            if m.track_number: tags.add(TRCK(encoding=3, text=f"{m.track_number}/{m.track_count}" if m.track_count else str(m.track_number)))
            if m.disc_number: tags.add(TPOS(encoding=3, text=f"{m.disc_number}/{m.disc_count}" if m.disc_count else str(m.disc_number)))
            if m.is_compilation: tags.add(TCMP(text='1'))
            
            if m.artwork_url:
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    r = requests.get(m.artwork_url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        tags.delall('APIC')
                        tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=r.content))
                except Exception as e: print(f"Artwork fetch error: {e}")
            tags.save(path, v2_version=3)
            
        elif ext == ".opus":
            import mutagen
            from mutagen.oggopus import OggOpus
            from mutagen.flac import Picture
            import base64
            
            try: tags = OggOpus(path)
            except: 
                tags = OggOpus()
                tags.save(path)
                tags = OggOpus(path)
                
            tags["title"] = m.title
            tags["artist"] = m.artist
            tags["albumartist"] = m.album_artist
            tags["album"] = m.album
            if m.release_date: tags["date"] = m.release_date.split('-')[0]
            if m.genre: tags["genre"] = m.genre
            if m.track_number: tags["tracknumber"] = str(m.track_number)
            if m.disc_number: tags["discnumber"] = str(m.disc_number)
            
            if m.artwork_url:
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    r = requests.get(m.artwork_url, headers=headers, timeout=10)
                    if r.status_code == 200:
                        p = Picture()
                        p.type = 3
                        p.mime = 'image/jpeg'
                        p.desc = 'Cover'
                        p.data = r.content
                        tags["metadata_block_picture"] = [base64.b64encode(p.write()).decode('ascii')]
                except Exception as e: print(f"Artwork fetch error: {e}")
            tags.save()

        # Rename and move to Music Tag Output
        safe_a = re.sub(r'[^a-zA-Z0-9\s\-]', '', m.artist)
        safe_t = re.sub(r'[^a-zA-Z0-9\s\-]', '', m.title)
        new_fname = f"{safe_a} - {safe_t}{ext}"
        dest = os.path.join(COMPLETED_DIR, new_fname)
        idx = 1
        while os.path.exists(dest):
            dest = os.path.join(COMPLETED_DIR, f"{new_fname[:-len(ext)]} ({idx}){ext}")
            idx += 1
        shutil.move(path, dest)
        return {"status": "ok"}
    except Exception as e:
        print(f"General Tagging/Move Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tags/{filename}")
def get_file_tags(filename: str):
    path = os.path.join(INPUT_DIR, filename)
    if not os.path.exists(path):
        path = os.path.join(COMPLETED_DIR, filename)
        if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    ext = os.path.splitext(path)[1].lower()
    info = {"filename": filename, "has_artwork": False, "tags": {}}
    try:
        if ext == ".mp3":
            tags = ID3(path)
            info["has_artwork"] = any(isinstance(f, APIC) for f in tags.values())
            # Convert to a simple dictionary mapping standard names
            info["tags"] = {
                "title": str(tags.get("TIT2", "")),
                "artist": str(tags.get("TPE1", "")),
                "album": str(tags.get("TALB", "")),
                "genre": str(tags.get("TCON", "")),
                "date": str(tags.get("TDRC", "")),
            }
        else:
            import mutagen
            audio = mutagen.File(path)
            info["has_artwork"] = "METADATA_BLOCK_PICTURE" in audio or "metadata_block_picture" in audio
            info["tags"] = {
                "title": str(audio.get("title", [""])[0]),
                "artist": str(audio.get("artist", [""])[0]),
                "album": str(audio.get("album", [""])[0]),
                "genre": str(audio.get("genre", [""])[0]),
                "date": str(audio.get("date", [""])[0]),
            }
    except Exception as e: info["error"] = str(e)
    return info

class EditTagsRequest(BaseModel):
    filename: str
    title: str
    artist: str
    album: str
    genre: str
    date: str

@app.post("/api/edit_tags")
def edit_file_tags(req: EditTagsRequest):
    path = os.path.join(COMPLETED_DIR, req.filename)
    if not os.path.exists(path): raise HTTPException(status_code=404, detail="File not found")
    
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".mp3":
            tags = ID3(path)
            tags.add(TIT2(encoding=3, text=req.title))
            tags.add(TPE1(encoding=3, text=req.artist))
            tags.add(TALB(encoding=3, text=req.album))
            tags.add(TCON(encoding=3, text=req.genre))
            tags.add(TDRC(encoding=3, text=req.date))
            tags.save(path, v2_version=3)
        else:
            import mutagen
            audio = mutagen.File(path)
            audio["title"] = req.title
            audio["artist"] = req.artist
            audio["album"] = req.album
            audio["genre"] = req.genre
            audio["date"] = req.date
            audio.save()

        # Rename file if artist or title changed
        safe_a = re.sub(r'[^a-zA-Z0-9\s\-]', '', req.artist)
        safe_t = re.sub(r'[^a-zA-Z0-9\s\-]', '', req.title)
        new_fname = f"{safe_a} - {safe_t}{ext}"
        if new_fname != req.filename:
            dest = os.path.join(COMPLETED_DIR, new_fname)
            idx = 1
            while os.path.exists(dest):
                dest = os.path.join(COMPLETED_DIR, f"{new_fname[:-len(ext)]} ({idx}){ext}")
                idx += 1
            shutil.move(path, dest)
            return {"status": "ok", "new_filename": os.path.basename(dest)}
        
        return {"status": "ok", "new_filename": req.filename}
    except Exception as e:
        print(f"Error editing tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    if not shutil.which("ffmpeg"): print("WARNING: ffmpeg not found in PATH.")
    def open_browser(): webbrowser.open("http://localhost:8000")
    threading.Timer(1.5, open_browser).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
