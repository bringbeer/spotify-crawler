# spotify-crawler

This repository contains tools to crawl Spotify playlists, build an index of albums and artists, download album cover images, and generate visual cluster/mosaic images from those covers.

Contents
- `src/crawl.py`: crawl Spotify playlists, produce `index.txt` and download cover images into `covers/`.
- `src/cluster_painter.py`: script to render a cluster image

Requirements
- Python 3.8+
- pip packages: `spotipy`, `Pillow`, `numpy`

Install dependencies:

```powershell
pip install spotipy Pillow numpy
```

Or run:

```powershell
pip install -r requirements.txt
```

`crawl.py` — Spotify crawler

What it does:
- Connects to the Spotify Web API (via `spotipy`) using your credentials.
- Walks the playlists you configure and generates an `index.txt` that contains an "Album Index" and an "Artist Index" with song counts.
- Downloads album cover images into a `covers/` directory as `.jpg` files. Filenames are sanitized (non-alphanumeric characters replaced with `_`).

Configuration / environment variables:
- `SPOTIPY_CLIENT_ID` — your Spotify client id
- `SPOTIPY_CLIENT_SECRET` — your Spotify client secret

Set them in PowerShell (example):

```powershell
$env:SPOTIPY_CLIENT_ID = "your-client-id"
$env:SPOTIPY_CLIENT_SECRET = "your-client-secret"
```

How to run:

```powershell
# from repository root
python .\src\crawl.py
```

Notes:
- You can insert playlist IDs — check the crawler file around the playlist configuration (line ~74 in the original script).
- Output files:
	- `index.txt` — album/artist index and song counts
	- `covers/` — downloaded `.jpg` album art (sanitized filenames)

`cluster_painter.py` / cluster script — create cluster images

What it does:
- Load `index.txt` and the `covers/` images and build a cluster/mosaic image where album covers are scaled by song count (more songs → larger image).

How to run (PowerShell):

```powershell
python .\src\cluster_painter.py
```

Outputs:
- `cluster.png` — the rendered cluster image.

Troubleshooting
- Encoding / mojibake: If `index.txt` contains non-ASCII characters (e.g. German umlauts), and you see warnings like `AuÃŸen` instead of `Außen`, the index file may have been saved in a different encoding. The code attempts UTF-8 first and falls back to `cp1252` / `latin-1`. If you still see mismatches, regenerate `index.txt` or ensure your editor saves it as UTF-8.
- Missing cover warnings: Filenames are sanitized by replacing non-alphanumeric characters with underscores. Example sanitized filename:

```
Außen_Top_Hits__innen_Geschmack__Gebäck_in_the_Days_1992___2002_.jpg
```

	If a cover file exists but the script can't find it, the cause may be:
	- Unicode normalization differences (NFC vs NFD). Consider normalizing names using `unicodedata.normalize('NFC', album_name)` before sanitizing.
	- Slight mismatch in sanitization rules — check the actual filename in `covers/`.

Adjusting visuals
- Background color: `src/cluster.py` creates the canvas using an RGB color. Change the `color=(R,G,B)` tuple in the `Image.new(...)` call to adjust brightness (e.g. `(20,20,20)` for almost-black).
- Size scaling: Edit `scale_dimension()` in the cluster scripts to change the min/max pixel sizes used for mapping counts to image sizes.

Developer notes
- Filenames are sanitized by replacing non-alphanumeric characters with underscores. If you prefer a different strategy, edit `get_cover_path` in `src/cluster_painter.py`.
