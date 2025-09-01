import os, base64, json, math, struct, requests

MURF_TTS_URL = os.getenv("MURF_TTS_URL", "").strip()
MURF_API_KEY = os.getenv("MURF_API_KEY", "").strip()

class MurfError(Exception):
    pass

def _tone_wav_b64(freq=440, ms=250, sr=22050):
    n = int(sr * (ms/1000))
    # 16-bit PCM mono WAV
    frames = bytearray()
    for i in range(n):
        s = int(32767 * math.sin(2*math.pi*freq*i/sr))
        frames += struct.pack("<h", s)
    byte_rate = sr * 2
    block_align = 2
    data = bytes(frames)
    # WAV header
    hdr = b"RIFF" + struct.pack("<I", 36+len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, sr, byte_rate, block_align, 16) + b"data" + struct.pack("<I", len(data))
    return base64.b64encode(hdr + data).decode("utf-8")

def synth_to_file_b64(text: str, voice_id: str, language: str, fmt: str = "mp3", sample_rate: int = 22050):
    # Debug bypass: return a local tone so you can test end to end without Murf
    if os.getenv("MURF_DEBUG", "0") == "1":
        return _tone_wav_b64(), "audio/wav"

    if not MURF_TTS_URL or not MURF_API_KEY:
        raise MurfError("Missing MURF_TTS_URL or MURF_API_KEY in .env")

    # Murf uses api-key header (not Bearer)
    headers = {
        "api-key": MURF_API_KEY,
        "Content-Type": "application/json"
    }

    # Keep keys liberal; map to Murf’s expected names
    payload = {
        "text": text,
        "voiceId": voice_id,       # <- Murf commonly uses voiceId (camelCase)
        "language": language,      # e.g., "en", or "en-US" depending on your voice
        "format": fmt,             # "mp3" | "wav"
        "sampleRate": sample_rate  # int
    }

    try:
        resp = requests.post(MURF_TTS_URL, headers=headers, data=json.dumps(payload), timeout=60)
    except Exception as e:
        raise MurfError(f"Network error calling Murf: {e}")

    if resp.status_code >= 300:
        # Surface Murf’s body to you for fast debugging
        raise MurfError(f"{resp.status_code} from Murf: {resp.text}")

    # Handle both direct base64 and URL response styles
    try:
        data = resp.json()
    except Exception as e:
        raise MurfError(f"Non-JSON response from Murf: {e}; body={resp.text[:400]}")

    if isinstance(data, dict) and "audio" in data:
        return data["audio"], f"audio/{fmt}"
    if isinstance(data, dict) and "audio_url" in data:
        a = requests.get(data["audio_url"], timeout=60)
        a.raise_for_status()
        return base64.b64encode(a.content).decode("utf-8"), f"audio/{fmt}"

    raise MurfError(f"Unexpected Murf response shape: {str(data)[:400]}")
