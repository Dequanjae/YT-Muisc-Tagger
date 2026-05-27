# YT-Music-Tagger Winows/Linux/MacOS
 YouTube Playlist, Apple Music Tagging, Downloading - I vibe-coded this to quickly add music to my Navidrome setup. I might update it to add more features like Spotify support for downloading and tags, but IDK

## ✨ Features

- **🚀 High-Fidelity Downloader**: Download entire YouTube playlists as **Opus** files (Superior quality at smaller sizes).
- **🏷️ Universal Smart Tagger**: Automatically identify songs and fetch official metadata/artwork for both MP3 and Opus formats.
- **💎 Premium UI**: A sleek, glassmorphism-inspired interface with smooth transitions and real-time updates.
- **📦 Portable**: Single server script, single HTML interface.

## 🛠️ Setup

1. **Install FFmpeg**: Ensure `ffmpeg` is installed and in your system PATH (required for audio conversion).
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Suite**:
   ```bash
   python combined_app.py
   ```
4. **Access the Interface**: Open `http://localhost:8000` in your browser.

## 📁 Project Structure

- `combined_app.py`: The unified FastAPI backend.
- `index.html`: The premium portable interface.
- `Playlist Download/`: The queue folder (where downloads land).
- `Music Tag Output/`: The final destination for tagged songs.

## 🚀 Workflow

1. Go to the **Downloader** tab and paste a YouTube Playlist URL.
2. Once downloads finish, switch to the **Tagger** tab.
3. Select a song from the queue, click **Auto Identify**, and confirm to save.
4. Your perfectly tagged music will be in the `Music Tag Output` folder!
