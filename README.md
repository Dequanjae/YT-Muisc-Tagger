# YT-Music-Tagger

A 3-in-1 automated YouTube Playlist Downloader and Apple Music Metadata Tagger. Vibe-coded to quickly download and perfectly tag music for personal media servers like **Navidrome**.

---

### 💻 Platform Support
Now supports **Windows**, **Linux**, and **macOS** with automated portable launchers.

---

## ✨ Features

- **🚀 High-Fidelity Downloader**: Download entire YouTube playlists as high-quality audio files.
- **🏷️ Universal Smart Tagger**: Automatically identify songs using Shazam and fetch official iTunes/Apple Music metadata & high-resolution artwork.
- **💎 Premium UI**: A sleek, modern glassmorphism-inspired dark interface with smooth animations and real-time download progress.
- **📦 Portable**: Single server script, single HTML interface, isolated virtual environment setups.

---

## 🛠️ Prerequisites

Before launching, make sure you have:
1. **Python 3** installed on your system.
2. **FFmpeg** installed and added to your system's PATH (required for audio conversion).

---

## 🚀 Quick Setup & Run

No need to manually create virtual environments or run pip install commands—the included launchers handle it all automatically.

### 🪟 Windows
1. Double-click `run_suite.bat`.
2. The script will check your Python installation, set up a virtual environment, install requirements, and open the app in your browser at `http://localhost:8000`.

### 🐧 Linux (Arch, Ubuntu, Fedora, etc.)
1. Open a terminal in the folder.
2. Make the script executable (only needed once):
   ```bash
   chmod +x run_suite.sh
   ```
3. Run the script:
   ```bash
   ./run_suite.sh
   ```

### 🍎 macOS
1. Open terminal in the folder.
2. Make the script executable:
   ```bash
   chmod +x run_suite.sh
   ```
3. Run the launcher:
   ```bash
   ./run_suite.sh
   ```

---

## 📁 Project Structure

- `combined_app.py`: FastAPI server combining the Downloader, Shazam API, and iTunes Metadata API.
- `index.html`: Sleek front-end client interface.
- `run_suite.sh`: Portable launcher for Linux and macOS.
- `run_suite.bat`: Portable launcher for Windows.
- `Playlist Download/`: Temporary queue folder where YouTube downloads land.
- `Music Tag Output/`: Final destination for processed, renamed, and tagged songs.

---

## 📖 How it Works

1. **Download**: Go to the **Downloader** tab, paste a YouTube Playlist/Video URL, and click **Download**.
2. **Identify**: Switch to the **Tagger** tab, select a song from the queue sidebar, and click **Auto Identify** to match it via Shazam.
3. **Refine / Search**: If a match is not found automatically, paste an Apple Music link directly into the search bar to fetch its metadata.
4. **Save**: Click the candidate card to write the ID3/Opus metadata and download the cover art. The file is automatically renamed to `Artist - Title` and moved to your `Music Tag Output` directory.
