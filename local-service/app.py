# app.py — Murf-only, adds /ws/stream (WebSocket) + keeps /speak (REST)
import os, io, json, base64, asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests
import websockets
from fastapi import FastAPI, HTTPException, Response, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# LLM (Gemini) for text generation before TTS
import google.generativeai as genai

app = FastAPI(title="Vibe Orchestrator (Murf-only + Streaming)")

# ========= Models =========
class SpeakIn(BaseModel):
    text: str = Field(..., description="User prompt / request")
    language: Optional[str] = Field(None, description="Locale like es-ES, es-MX, fr-FR, en-UK, en-SCOTT, etc.")
    voice_id: Optional[str] = Field(None, description="Force a Murf voice id (overrides picker)")
    style: Optional[str] = Field(None, description="Voice style (Conversational, Promo, Calm, …)")
    format: Optional[str] = Field(None, description="'wav' or 'mp3' (default wav)")
    files: Optional[List[str]] = Field(None, description="Optional file paths for brief context")

class SpeakOut(BaseModel):
    audio_b64: str
    mime: str
    text: str

# ========= Voice catalog loader =========
ROOT = Path(__file__).parent

def _load_catalog() -> Dict[str, List[Dict[str, Any]]]:
    env_json = os.getenv("MURF_VOICE_CATALOG")
    if env_json:
        try:
            return json.loads(env_json)
        except Exception as e:
            raise HTTPException(500, f"Invalid MURF_VOICE_CATALOG JSON: {e}")
    f = ROOT / "voices.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            raise HTTPException(500, f"voices.json parse error: {e}")
    raise HTTPException(500, "Voice catalog not found. Add voices.json or MURF_VOICE_CATALOG env.")

VOICES: Dict[str, List[Dict[str, Any]]] = _load_catalog()

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _upper_key(s: str) -> str:
    return s.upper()

def _find_voices_for_locale(locale: str) -> List[Dict[str, Any]]:
    want = _upper_key(locale)
    out: List[Dict[str, Any]] = []

    # exact section
    if want in VOICES:
        out.extend(VOICES[want])

    # multi-locale
    for v in VOICES.get("multi-locale", []):
        if any(_upper_key(x) == want for x in v.get("locales", [])):
            out.append(v)

    # scan others
    for sect, arr in VOICES.items():
        if sect in (want, "multi-locale"):
            continue
        for v in arr:
            if any(_upper_key(x) == want for x in v.get("locales", [])):
                out.append(v)

    # base-lang fallback (es-AR -> any es-XX)
    if not out and "-" in want:
        base = want.split("-")[0]
        for arr in VOICES.values():
            for v in arr:
                for loc in v.get("locales", []):
                    if _upper_key(loc).startswith(base + "-"):
                        out.append(v)
                        break
    return out

def _pick_voice(locale: Optional[str], style: Optional[str], override: Optional[str]) -> str:
    if override:
        return override
    loc = _norm(locale or "en-US").upper()
    candidates = _find_voices_for_locale(loc)
    if not candidates:
        raise HTTPException(422, f"No Murf voice supports locale '{locale}'. Add to voices.json or pass voice_id.")
    sty = _norm(style).lower()
    if sty:
        for v in candidates:
            if sty in [s.lower() for s in v.get("styles", [])]:
                return v["id"]
    return candidates[0]["id"]

# ========= Gemini (text generation) =========
def _ensure_gemini():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise HTTPException(500, "GEMINI_API_KEY not set")
    genai.configure(api_key=key)

LANG_NAMES = {
    "en": "English","fr":"French","de":"German","es":"Spanish","it":"Italian",
    "pt":"Portuguese","zh":"Chinese","nl":"Dutch","hi":"Hindi","ko":"Korean",
    "ta":"Tamil","pl":"Polish","bn":"Bengali","ja":"Japanese","tr":"Turkish","id":"Indonesian"
}

def _base_lang(code: str) -> str:
    code = _norm(code).lower()
    return code.split("-")[0] if code else "en"

def run_gemini(prompt: str, language: Optional[str], files: Optional[List[str]]) -> str:
    _ensure_gemini()
    model = genai.GenerativeModel("gemini-1.5-flash")

    ctx_parts: List[str] = []
    import re
    def clean_code(code: str) -> str:
        # Remove docstrings and quoted blocks (triple quotes)
        code = re.sub(r'"""[\s\S]*?"""', '', code)
        code = re.sub(r"'''[\s\S]*?'''", '', code)
        # Remove single/double quoted lines
        code = re.sub(r'^\s*["\"][^"\"]*["\"]\s*$', '', code, flags=re.MULTILINE)
        lines = code.splitlines()
        cleaned = []
        for line in lines:
            l = line.strip()
            # Remove lines that are only asterisks, hyphens, slashes, or boilerplate
            if l in ("*", "-", "--", "***", "#", "# ...", "# Copyright", "# License", "/", "//", "///", "////", "\\", "\\\\"):
                continue
            if l.startswith("#") and ("copyright" in l.lower() or "license" in l.lower()):
                continue
            if l == "" or l == "...":
                continue
            # Remove lines that are mostly slashes or separators
            if re.match(r'^[#/\\\-\s]+$', l):
                continue
            # Remove lines that start and end with quotes
            if (l.startswith("'") and l.endswith("'")) or (l.startswith('"') and l.endswith('"')):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    for p in (files or [])[:3]:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read(5000)
                ctx_parts.append(clean_code(raw))
        except Exception as e:
            ctx_parts.append(f"[{p} error: {e}]")
    ctx = "\n\n".join(ctx_parts)

    loc = _norm(language or "en-US").lower()
    base = _base_lang(loc)
    lang_name = LANG_NAMES.get(base, base)

    system = (
        f"You are Vibe, a multilingual coding copilot and senior software engineer.\n"
        f"IMPORTANT: Reply entirely in {lang_name} ({loc}). "
        "Speak in a natural, conversational way, as if mentoring a junior developer.\n"
        "Be concise, practical, and code-aware. Prefer bullet points, diffs, or actionable commands.\n"
        "Do NOT just translate; perform code-aware reasoning and avoid reading out code symbols, asterisks, boilerplate, quotes, or docstrings.\n"
        "- When explaining a repo/file, focus on its purpose, tech stack, key modules, data flow, design patterns, code smells, risks, and next steps.\n"
        "  Reference filenames/functions if context is provided, but do not read out raw code, quotes, or docstrings unless asked.\n"
        "- If information is missing (e.g., repo URL), ask once, then stop.\n"
        "- If asked for code, provide only the relevant code, not the entire file.\n"
    )
    user = f"User:\n{prompt}"
    if ctx:
        user += f"\n\nContext:\n{ctx}"

    resp = model.generate_content(f"{system}\n\n{user}")
    text = (getattr(resp, "text", "") or "").strip()
    if not text:
        raise HTTPException(502, "Gemini returned empty text")
    return text

# ========= Murf REST (non-stream) =========
def murf_generate(text: str, language: Optional[str], voice_id: Optional[str],
                  fmt: Optional[str], style: Optional[str]) -> (str, str):
    api_key = os.getenv("MURF_API_KEY")
    if not api_key:
        raise HTTPException(500, "MURF_API_KEY not set")

    fmt_norm = (fmt or "wav").lower()
    if fmt_norm not in ("wav", "mp3"):
        fmt_norm = "wav"

    chosen = _pick_voice(language, style, voice_id)

    url = "https://api.murf.ai/v1/speech/generate"
    payload = {
        "text": text,
        "voiceId": chosen,
        "format": fmt_norm,
        "encodeAsBase64": True,
    }
    if style:
        payload["speechCustomization"] = {"style": style}

    headers = {"api-key": api_key, "Content-Type": "application/json"}
    r = requests.post(url, json=payload, headers=headers, timeout=45)
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise HTTPException(502, f"Murf TTS failed: {e} | {r.text[:400]}")

    data = r.json()
    b64 = data.get("encodedAudio") or data.get("encoded_audio")
    if not b64:
        # fallback if only a URL was returned
        audio_url = data.get("audioFile") or data.get("audio_file")
        if audio_url:
            audio = requests.get(audio_url, timeout=45).content
            b64 = base64.b64encode(audio).decode("utf-8")

    if not b64:
        raise HTTPException(502, "Murf returned no audio")

    mime = "audio/wav" if fmt_norm == "wav" else "audio/mpeg"
    return b64, mime

# ========= Murf WebSocket proxy (/ws/stream) =========
MURF_WS = "wss://api.murf.ai/v1/speech/stream-input"
SAMPLE_RATE = 44100
CHANNEL = "MONO"

@app.websocket("/ws/stream")
async def ws_stream(local_ws: WebSocket):
    """
    Client connects here, sends a single JSON:
    {
      "text": "...", "language": "es-ES", "voice_id": "...", "style": "Conversational", "format": "WAV"
    }
    We forward to Murf WS and echo back frames:
      {"info": {...}} (once, transcript + chosen voice)
      {"audio_b64": "..."} (many)
      {"final": true} (once)
    """
    await local_ws.accept()
    try:
        first = await local_ws.receive_json()
        text   = _norm(first.get("text"))
        lang   = _norm(first.get("language") or "en-US")
        style  = _norm(first.get("style"))
        fmt    = (first.get("format") or "WAV").upper()
        voice  = _norm(first.get("voice_id"))
        files  = first.get("files") or []

        if not text:
            await local_ws.send_json({"error": "Missing 'text'."})
            await local_ws.close()
            return

        # If the text looks like an instruction (your normal use), generate with Gemini first
        # (If you already pass ready-to-speak text, comment the next line)
        text_to_speak = run_gemini(text, lang, files)

        chosen = _pick_voice(lang, style, voice)
        api_key = os.getenv("MURF_API_KEY")
        if not api_key:
            await local_ws.send_json({"error": "MURF_API_KEY not set"})
            await local_ws.close()
            return

        # Tell the client what we’re about to stream
        await local_ws.send_json({
            "info": {
                "transcript": text_to_speak,
                "voice_id": chosen,
                "mime": "audio/wav" if fmt == "WAV" else "audio/mpeg",
                "sample_rate": SAMPLE_RATE,
                "channel": CHANNEL,
                "format": fmt
            }
        })

        qs = f"?api-key={api_key}&sample_rate={SAMPLE_RATE}&channel_type={CHANNEL}&format={fmt}"
        async with websockets.connect(MURF_WS + qs) as murf:
            # optional voice config
            voice_cfg = {
                "voice_config": {
                    "voiceId": chosen,
                    "style": style or "Conversational",
                    "rate": 0, "pitch": 0, "variation": 1
                }
            }
            await murf.send(json.dumps(voice_cfg))

            # now the text
            await murf.send(json.dumps({"text": text_to_speak, "end": True}))

            # forward streaming frames to the client
            while True:
                resp = await murf.recv()
                data = json.loads(resp)
                if "audio" in data:
                    await local_ws.send_json({"audio_b64": data["audio"]})
                if data.get("final"):
                    await local_ws.send_json({"final": True})
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await local_ws.send_json({"error": str(e)})
        finally:
            await local_ws.close()

# ========= REST API (non-stream) =========
@app.get("/")
def root():
    return {"ok": True, "endpoints": ["/health", "/voices/which?lang=es-ES&style=Promo", "/speak", "WS: /ws/stream"]}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/voices/which")
def voices_which(lang: str = Query("en-US"), style: Optional[str] = Query(None)):
    vid = _pick_voice(lang, style, None)
    return {"lang": lang, "style": style, "voice_id": vid}

@app.post("/speak", response_model=SpeakOut)
def speak(inp: SpeakIn):
    # 1) LLM -> text in target language
    answer = run_gemini(inp.text, inp.language, inp.files)
    # 2) Murf (one-shot)
    b64, mime = murf_generate(answer, inp.language, inp.voice_id, inp.format, inp.style)
    return SpeakOut(audio_b64=b64, mime=mime, text=answer)

# ========= Optional static =========
STATIC_DIR = ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    ico = STATIC_DIR / "favicon.ico"
    if ico.exists():
        return FileResponse(str(ico), media_type="image/x-icon")
    return Response(status_code=204)

# Added by LangChain agent
def new_function():
    print('Hello from LangChain agent!')

# Added by LangChain agent
def new_function():
    print('Hello from LangChain agent!')

# Added by LangChain agent
def new_function():
    print('Hello from LangChain agent!')

# Added by LangChain agent
def new_function():
    print('Hello from LangChain agent!')

# Added by LangChain agent
def new_function():
    print('Hello from LangChain agent!')
