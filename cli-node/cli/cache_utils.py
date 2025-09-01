import os
import hashlib
import json
from pathlib import Path

def get_cache_dir():
    cache_dir = Path(__file__).parent / "_cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir

def make_cache_key(prompt, language, file_path, voice_id, style, fmt):
    key_str = json.dumps({
        "prompt": prompt,
        "language": language,
        "file": file_path,
        "voice_id": voice_id,
        "style": style,
        "format": fmt
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()

def cache_exists(key):
    cache_dir = get_cache_dir()
    return (cache_dir / f"{key}.json").exists()

def load_cache(key):
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_cache(key, transcript, audio_b64, mime):
    cache_dir = get_cache_dir()
    cache_file = cache_dir / f"{key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({
            "transcript": transcript,
            "audio_b64": audio_b64,
            "mime": mime
        }, f, ensure_ascii=False)