import os
import pytest
from cache_utils import make_cache_key, save_cache, load_cache, cache_exists, get_cache_dir

def test_cache_key_uniqueness():
    key1 = make_cache_key('hello', 'en-US', 'file1.py', 'voice1', 'style1', 'WAV')
    key2 = make_cache_key('hello', 'en-US', 'file2.py', 'voice1', 'style1', 'WAV')
    assert key1 != key2


def test_cache_save_and_load():
    key = make_cache_key('test', 'en-US', 'file.py', 'voice', 'style', 'WAV')
    transcript = 'This is a test.'
    audio_b64 = 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA='
    mime = 'audio/wav'
    save_cache(key, transcript, audio_b64, mime)
    assert cache_exists(key)
    loaded = load_cache(key)
    assert loaded['transcript'] == transcript
    assert loaded['audio_b64'] == audio_b64
    assert loaded['mime'] == mime


def test_cache_dir_created():
    cache_dir = get_cache_dir()
    assert os.path.exists(cache_dir)
    assert os.path.isdir(cache_dir)


def test_cache_miss():
    key = make_cache_key('notfound', 'en-US', 'nofile.py', 'voice', 'style', 'WAV')
    assert load_cache(key) is None

# Add more tests for CLI error handling and voice selection as needed
