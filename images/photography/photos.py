#!/usr/bin/env python3
"""
Prepare this folder (images/photography/) for the website and rebuild the gallery manifest.

Usage (from this folder, or pass the path from anywhere):
    python3 photos.py            # do it
    python3 photos.py --dry-run  # only print what would happen

Workflow: drop new photos/videos (e.g. AirDropped IMG_1234.HEIC / IMG_1235.MOV) into
this folder, optionally add a caption file with the same name (IMG_1234.txt),
then run this script. It will:

  1. Convert iPhone formats to ones every browser can show (uses macOS built-ins):
       HEIC / HEIF / DNG / TIFF -> JPEG   (sips)
       MOV                       -> MP4   (avconvert, H.264 1080p; ffmpeg if installed)
     New photos are also shrunk to MAX_IMAGE_SIZE px on the long side.
  2. Give every file that isn't already named with a number the next number, oldest
     capture date first, so the newest file gets the biggest number (= shown first).
     A matching .txt caption is renamed along with it.
  3. Move the originals to images/photography/_originals/ (ignored by git).
  4. Rewrite images/photography/manifest.js, which photography.html reads.

Numbers decide the order: the largest number is shown first.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

# The script lives in the photo folder itself.
PHOTO_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINALS_DIR = os.path.join(PHOTO_DIR, "_originals")
MANIFEST = os.path.join(PHOTO_DIR, "manifest.js")

MAX_IMAGE_SIZE = 2560          # px, long edge, applied to new photos only
JPEG_QUALITY = 85
VIDEO_PRESET = "Preset1920x1080"  # avconvert preset (H.264)

# Formats browsers can display directly.
WEB_IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
WEB_VIDEOS = {".mp4", ".webm", ".m4v"}
# Formats we convert (iPhone photos, ProRAW, iPhone videos).
CONVERT_IMAGES = {".heic", ".heif", ".dng", ".tif", ".tiff"}
CONVERT_VIDEOS = {".mov"}

MEDIA = WEB_IMAGES | WEB_VIDEOS | CONVERT_IMAGES | CONVERT_VIDEOS

GITHUB_WARN_MB = 50
GITHUB_LIMIT_MB = 100

DRY_RUN = "--dry-run" in sys.argv


def log(msg):
    print(("[dry-run] " if DRY_RUN else "") + msg)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def have(tool):
    return shutil.which(tool) is not None


def split(name):
    stem, ext = os.path.splitext(name)
    return stem, ext.lower()


def is_number(stem):
    return re.fullmatch(r"\d+", stem) is not None


def media_files():
    out = []
    for name in os.listdir(PHOTO_DIR):
        path = os.path.join(PHOTO_DIR, name)
        if name.startswith(".") or not os.path.isfile(path):
            continue
        if split(name)[1] in MEDIA:
            out.append(name)
    return out


def capture_time(path):
    """Best guess at when the photo/video was taken."""
    if have("mdls"):
        r = run(["mdls", "-raw", "-name", "kMDItemContentCreationDate", path])
        try:
            return datetime.strptime(r.stdout.strip(), "%Y-%m-%d %H:%M:%S %z").timestamp()
        except ValueError:
            pass
    st = os.stat(path)
    return getattr(st, "st_birthtime", st.st_mtime)


def image_long_edge(path):
    r = run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path])
    nums = [int(n) for n in re.findall(r"pixel(?:Width|Height):\s*(\d+)", r.stdout)]
    return max(nums) if nums else 0


def stash_original(path):
    """Move a source file into _originals/ without overwriting anything there."""
    if DRY_RUN:
        return
    os.makedirs(ORIGINALS_DIR, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    dest = os.path.join(ORIGINALS_DIR, stem + ext)
    i = 1
    while os.path.exists(dest):
        dest = os.path.join(ORIGINALS_DIR, f"{stem}_{i}{ext}")
        i += 1
    shutil.move(path, dest)


def convert_image(src, dest_stem):
    """HEIC/DNG/etc -> JPEG (or resize a new JPEG). Returns new filename or None."""
    dest_name = dest_stem + ".jpg"
    dest = os.path.join(PHOTO_DIR, dest_name)
    if not have("sips"):
        print(f"  ! can't convert {os.path.basename(src)}: 'sips' not found (macOS only)")
        return None
    cmd = ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(JPEG_QUALITY)]
    if image_long_edge(src) > MAX_IMAGE_SIZE:
        cmd += ["-Z", str(MAX_IMAGE_SIZE)]
    cmd += [src, "--out", dest]
    log(f"  convert {os.path.basename(src)} -> {dest_name}")
    if DRY_RUN:
        return dest_name
    r = run(cmd)
    if r.returncode != 0 or not os.path.exists(dest):
        print(f"  ! sips failed on {os.path.basename(src)}: {r.stderr.strip()}")
        return None
    return dest_name


def convert_video(src, dest_stem):
    """MOV -> H.264 MP4. Returns new filename or None."""
    dest_name = dest_stem + ".mp4"
    dest = os.path.join(PHOTO_DIR, dest_name)
    log(f"  convert {os.path.basename(src)} -> {dest_name} (this can take a while)")
    if DRY_RUN:
        return dest_name
    if have("avconvert"):
        r = run(["avconvert", "-s", src, "-o", dest, "-p", VIDEO_PRESET, "--replace"])
    elif have("ffmpeg"):
        r = run(["ffmpeg", "-y", "-i", src, "-c:v", "libx264", "-crf", "23",
                 "-vf", "scale='min(1920,iw)':-2", "-c:a", "aac",
                 "-movflags", "+faststart", dest])
    else:
        print(f"  ! can't convert {os.path.basename(src)}: need avconvert (macOS) or ffmpeg")
        return None
    if r.returncode != 0 or not os.path.exists(dest):
        print(f"  ! video conversion failed on {os.path.basename(src)}: {(r.stderr or r.stdout).strip()}")
        if os.path.exists(dest):
            os.remove(dest)
        return None
    return dest_name


def process(name, dest_stem):
    """Convert/rename one media file to dest_stem + web extension."""
    src = os.path.join(PHOTO_DIR, name)
    stem, ext = split(name)

    if ext in CONVERT_IMAGES:
        out = convert_image(src, dest_stem)
    elif ext in CONVERT_VIDEOS:
        out = convert_video(src, dest_stem)
    elif ext in WEB_IMAGES and ext in {".jpg", ".jpeg"} and have("sips") \
            and image_long_edge(src) > MAX_IMAGE_SIZE and not is_number(stem):
        out = convert_image(src, dest_stem)       # shrink big new JPEGs
    else:
        # Already web-friendly: just rename (normalising the extension).
        ext = ".jpg" if ext == ".jpeg" else ext
        out = dest_stem + ext
        if out != name:
            log(f"  rename  {name} -> {out}")
            if not DRY_RUN:
                os.rename(src, os.path.join(PHOTO_DIR, out))
        return out

    if out is None:
        # Conversion failed: keep the original under its number so nothing is lost.
        fallback = dest_stem + ext
        print(f"  ! keeping original as {fallback} (may not display in every browser)")
        if not DRY_RUN and fallback != name:
            os.rename(src, os.path.join(PHOTO_DIR, fallback))
        return fallback

    stash_original(src)
    return out


def move_caption(old_stem, new_stem, keep_source=False):
    src = os.path.join(PHOTO_DIR, old_stem + ".txt")
    if not os.path.exists(src) or old_stem == new_stem:
        return
    log(f"  caption {old_stem}.txt -> {new_stem}.txt")
    if not DRY_RUN:
        dest = os.path.join(PHOTO_DIR, new_stem + ".txt")
        shutil.copy(src, dest) if keep_source else os.rename(src, dest)


def main():
    files = media_files()

    # 1. Numbered files in a format browsers can't show (e.g. someone saved 40.HEIC).
    for name in files:
        stem, ext = split(name)
        if is_number(stem) and ext in CONVERT_IMAGES | CONVERT_VIDEOS:
            log(f"{name}: converting in place")
            process(name, stem)

    # 2. New, un-numbered files: number them from max+1, oldest first.
    files = media_files()
    numbers = [int(split(n)[0]) for n in files if is_number(split(n)[0])]
    next_num = max(numbers, default=0) + 1
    new = [n for n in files if not is_number(split(n)[0])]
    new.sort(key=lambda n: (capture_time(os.path.join(PHOTO_DIR, n)), n))

    if new:
        print(f"Found {len(new)} new file(s); numbering from {next_num}.")
    # How many new files share each stem (e.g. a Live Photo's IMG_1.HEIC + IMG_1.MOV).
    stem_count = {}
    for n in new:
        stem_count[split(n)[0]] = stem_count.get(split(n)[0], 0) + 1

    for name in new:
        stem = split(name)[0]
        num = str(next_num)
        next_num += 1
        log(f"{name} -> #{num}")
        process(name, num)
        stem_count[stem] -= 1
        # Copy the caption to every file sharing the stem; move it on the last one.
        move_caption(stem, num, keep_source=stem_count[stem] > 0)

    # 3. Rebuild manifest.
    write_manifest()


def write_manifest():
    entries = []
    for name in media_files():
        stem, ext = split(name)
        if not is_number(stem):
            print(f"  ! skipping {name} in manifest (not numbered)")
            continue
        if ext in CONVERT_IMAGES | CONVERT_VIDEOS:
            print(f"  ! {name} is not a web format; it may not display in Chrome/Firefox")
        caption_path = os.path.join(PHOTO_DIR, stem + ".txt")
        caption = ""
        if os.path.exists(caption_path):
            with open(caption_path, encoding="utf-8", errors="replace") as f:
                caption = f.read().strip()
        kind = "video" if ext in WEB_VIDEOS | CONVERT_VIDEOS else "image"
        entries.append({"n": int(stem), "file": name, "type": kind, "caption": caption})

        size_mb = os.path.getsize(os.path.join(PHOTO_DIR, name)) / 1e6
        if size_mb > GITHUB_LIMIT_MB:
            print(f"  !! {name} is {size_mb:.0f}MB: over GitHub's {GITHUB_LIMIT_MB}MB limit, push will fail")
        elif size_mb > GITHUB_WARN_MB:
            print(f"  ! {name} is {size_mb:.0f}MB: large for a website")

    entries.sort(key=lambda e: (-e["n"], e["file"]))
    seen = set()
    for e in entries:
        if e["n"] in seen:
            print(f"  ! number {e['n']} is used by more than one file")
        seen.add(e["n"])
    for e in entries:
        del e["n"]

    body = ("// Generated by photos.py -- don't edit by hand, run `python3 photos.py` instead.\n"
            "// Largest number first. Captions come from <number>.txt.\n"
            "window.PHOTOS = " + json.dumps(entries, indent=2, ensure_ascii=False) + ";\n")
    log(f"Writing manifest with {len(entries)} item(s).")
    if not DRY_RUN:
        with open(MANIFEST, "w", encoding="utf-8") as f:
            f.write(body)


if __name__ == "__main__":
    main()
