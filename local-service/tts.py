# local-service/tts.py
import os, base64
from io import BytesIO
from typing import Optional, Tuple

# --- Base interface -----------------------------------------------------------
class TTSProvider:
    name = "base"
    def speak(self, text: str, lang: Optional[str], fmt: str) -> Tuple[bytes, str]:
        raise NotImplementedError

# --- Offline, WAV (best for Windows + direct playback) ------------------------
class Pyttsx3TTS(TTSProvider):
    name = "pyttsx3"
    def speak(self, text: str, lang: Optional[str], fmt: str) -> Tuple[bytes, str]:
        import pyttsx3, tempfile, os
        engine = pyttsx3.init()
        # Try to pick a voice matching language
        if lang:
            try:
                for v in engine.getProperty("voices"):
                    langs = []
                    for L in getattr(v, "languages", []):
                        try:
                            langs.append(L.decode(errors="ignore"))
                        except Exception:
                            langs.append(str(L))
                    if any(lang.lower() in (L or "").lower() for L in langs):
                        engine.setProperty("voice", v.id)
                        break
            except Exception:
                pass

        tmp = tempfile.mktemp(suffix=".wav")
        try:
            engine.save_to_file(text, tmp)
            engine.runAndWait()
            data = open(tmp, "rb").read()
            return data, "audio/wav"
        finally:
            try: os.remove(tmp)
            except Exception: pass

# --- Online, MP3 (quick fallback) --------------------------------------------
class GTtsTTS(TTSProvider):
    name = "gtts"
    def speak(self, text: str, lang: Optional[str], fmt: str) -> Tuple[bytes, str]:
        from gtts import gTTS
        buf = BytesIO()
        kwargs = {"text": text}
        if lang: kwargs["lang"] = lang
        gTTS(**kwargs).write_to_fp(buf)
        return buf.getvalue(), "audio/mpeg"

# --- Murf stub (fill in later) -----------------------------------------------
class MurfTTS(TTSProvider):
    name = "murf"
    """
    Placeholder – you’ll wire this to **Murf’s REST/WebSocket**.
    The method should return (audio_bytes, mime) just like the others.
    """
    def speak(self, text: str, lang: Optional[str], fmt: str) -> Tuple[bytes, str]:
        api_key = os.getenv("MURF_API_KEY")
        if not api_key:
            raise RuntimeError("MURF_API_KEY not set")
        # TODO: Implement Murf REST or WS call here; respect `lang` and `fmt`.
        # For tomorrow’s demo, keep Pyttsx3 (WAV) as default and swap to Murf after.
        raise NotImplementedError("Murf provider not implemented yet.")

# --- Factory -----------------------------------------------------------------
def get_tts_provider(fmt: str) -> TTSProvider:
    want = (os.getenv("TTS_PROVIDER") or "").lower().strip()
    # Prefer offline WAV so we can play without external player
    if want == "pyttsx3" or (not want and fmt == "wav"):
        return Pyttsx3TTS()
    if want == "murf":
        return MurfTTS()
    return GTtsTTS()

# Added by LangChain agent
def new_function():
    print('Hello from LangChain agent!')
