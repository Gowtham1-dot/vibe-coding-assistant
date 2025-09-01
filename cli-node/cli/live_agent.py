# live_agent.py
# Live voice conversation agent using Google SpeechRecognition (STT) and your existing TTS backend
import speech_recognition as sr
import requests
import os
import tempfile
import time





def listen_vosk():
    try:
        from vosk_stt import transcribe_vosk
    except ImportError:
        print("vosk_stt.py not found or Vosk not installed.")
        return None
    try:
        duration = input("How many seconds to record? (default 5): ").strip()
        duration = int(duration) if duration else 5
    except Exception:
        duration = 5
    try:
        text = transcribe_vosk(duration=duration)
        return text
    except Exception as e:
        print(f"Vosk error: {e}")
        return None

def listen_google():
    recognizer = sr.Recognizer()
    user_input = input("Type 's' to speak, 'q' to quit, or Enter to skip: ").strip().lower()
    if user_input == "q":
        return "__QUIT__"
    if user_input != "s":
        # Only listen if user types 's'
        return None
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1.0  # Waits longer for pauses
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        print("You said:", text)
        return text
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"Google STT error: {e}")
        return None


import re
# Language mapping for Murf/Gemini
LANG_MAP = {
    "english": "en-US", "en": "en-US",
    "hindi": "hi-IN", "hi": "hi-IN",
    "spanish": "es-ES", "es": "es-ES",
    "french": "fr-FR", "fr": "fr-FR",
    "german": "de-DE", "de": "de-DE",
    "italian": "it-IT", "it": "it-IT",
    "portuguese": "pt-PT", "pt": "pt-PT",
    "chinese": "zh-CN", "zh": "zh-CN",
    "tamil": "ta-IN", "ta": "ta-IN",
    "bengali": "bn-IN", "bn": "bn-IN",
    "japanese": "ja-JP", "ja": "ja-JP",
    "korean": "ko-KR", "ko": "ko-KR",
    "turkish": "tr-TR", "tr": "tr-TR",
    "polish": "pl-PL", "pl": "pl-PL",
    "dutch": "nl-NL", "nl": "nl-NL",
    "indonesian": "id-ID", "id": "id-ID"
}

def extract_lang_from_prompt(prompt):
    # Look for "in <language>" at the end or in the prompt
    m = re.search(r"in ([a-zA-Z]+)", prompt, re.IGNORECASE)
    if m:
        lang_word = m.group(1).lower()
        return LANG_MAP.get(lang_word)
    return None

def tts_stream(prompt, lang=None, voice=None, style=None, fmt="WAV"):
    # Detect language from prompt if not explicitly set
    detected_lang = extract_lang_from_prompt(prompt)
    if detected_lang:
        lang = detected_lang
    # Detect file mentions in the prompt (e.g., "app.py", "explain local-service/app.py")
    file_pattern = re.compile(r"([\w\-/\\]+\.py)", re.IGNORECASE)
    files = []
    for match in file_pattern.findall(prompt):
        # Try to resolve relative to project root or cli dir
        if os.path.isfile(match):
            files.append(match)
        else:
            # Try common locations
            possible = os.path.join("..", "local-service", match)
            if os.path.isfile(possible):
                files.append(possible)
    # Call your FastAPI backend for TTS (adjust endpoint as needed)
    ws_url = "ws://127.0.0.1:8001/ws/stream"
    import websockets, asyncio, json, base64
    async def run():
        payload = {"text": prompt, "language": lang, "voice_id": voice, "style": style, "format": fmt}
        if files:
            payload["files"] = files
        async with websockets.connect(ws_url) as ws:
            await ws.send(json.dumps(payload))
            pa = None
            stream = None
            first = True
            import pyaudio
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if "error" in data:
                    print("Error:", data["error"])
                    break
                if "info" in data:
                    info = data["info"]
                    transcript = (info.get("transcript") or "").strip()
                    if transcript:
                        print("\n--- Transcript ---\n" + transcript + "\n")
                    pa = pyaudio.PyAudio()
                    stream = pa.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=int(info.get("sample_rate", 44100)),
                        output=True,
                    )
                    continue
                if "audio_b64" in data:
                    chunk = base64.b64decode(data["audio_b64"])
                    if first and len(chunk) > 44:
                        chunk = chunk[44:]
                        first = False
                    if stream:
                        stream.write(chunk)
                    continue
                if data.get("final"):
                    break
            if stream:
                stream.stop_stream()
                stream.close()
            if pa:
                pa.terminate()
    asyncio.run(run())




def live_agent():
    print("Live Agent Conversation (STT + TTS)")
    print("Default: Vosk STT (offline, more robust for CLI)")
    print("Type 'g' to use Google STT (online) for this session, or Enter to use Vosk.")
    stt_choice = input("STT engine: ").strip().lower()
    if stt_choice == "g":
        stt_func = listen_google
        print("Using Google STT (online)")
    else:
        stt_func = listen_vosk
        print("Using Vosk STT (offline)")
    while True:
        while True:
            user_text = stt_func()
            if user_text == "__QUIT__":
                print("Goodbye!")
                return
            if not user_text:
                continue
            print(f"Recognized: {user_text}")
            action = input("Type 'r' to rephrase, 'q' to quit, Enter to confirm: ").strip().lower()
            if action == "q":
                print("Goodbye!")
                return
            if action == "r":
                continue
            break
        if user_text.lower() in ["exit", "quit", "stop"]:
            print("Goodbye!")
            break
        tts_stream(user_text)
        time.sleep(0.5)

if __name__ == "__main__":
    live_agent()
