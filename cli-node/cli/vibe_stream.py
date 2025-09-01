def _to_str_or_none(val):
    if hasattr(val, "__class__") and val.__class__.__name__ == "OptionInfo":
        return None
    return val
# cli/vibe_stream.py
import os, json, base64, asyncio, websockets, typer
import logging

# Setup logging (file and console)
LOG_FILE = os.path.join(os.path.dirname(__file__), 'vibe_cli.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
from cache_utils import make_cache_key, cache_exists, load_cache, save_cache
from typing import Optional, List
import re

# Language mapping for auto-detection
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
    # Add more as needed
}

def extract_lang_from_prompt(prompt: str) -> Optional[str]:
    # Look for 'in <language>' at the end or in the prompt
    m = re.search(r"in ([a-zA-Z\-]+)$", prompt.strip(), re.IGNORECASE)
    if m:
        lang_word = m.group(1).lower()
        return LANG_MAP.get(lang_word)
    # Also check for 'in <language>' anywhere
    for word in LANG_MAP:
        if f"in {word}" in prompt.lower():
            return LANG_MAP[word]
    return None

# Pretty unicode on Windows terminals
try:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

APP = typer.Typer(no_args_is_help=True, add_completion=False)

VOICE_ID_FILE = os.path.join(os.path.dirname(__file__), '.last_voice_id')

@APP.command(help="Stream TTS from the local FastAPI WS (/ws/stream) with inline playback (no external player).")
def stream(
    prompt: str = typer.Argument(None, help="Prompt for TTS (leave blank to use --stt-input)"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l"),
    api_ws: str = typer.Option("ws://127.0.0.1:8001/ws/stream", "--api-ws"),
    voice: Optional[str] = typer.Option(None, "--voice-id"),
    style: Optional[str] = typer.Option(None, "--style"),
    fmt: str = typer.Option("WAV", "--format"),
    files: List[str] = typer.Option(None, "--file", "-f", help="Optional file(s) for context", show_default=False),
    stt_input: bool = typer.Option(False, "--stt-input", help="Use Google STT to capture spoken prompt"),
    show_transcript: bool = typer.Option(True, "--show-transcript/--hide-transcript", help="Show transcript in console (default: on)"),
):
    """
    Connects to your FastAPI proxy at /ws/stream which relays to Murf's WS API.
    Plays audio inline using PyAudio; never launches an external media player.
    """


    # Ensure all possibly OptionInfo variables are safe before any logic
    api_ws = _to_str_or_none(api_ws)
    if api_ws is None:
        api_ws = "ws://127.0.0.1:8001/ws/stream"
    voice = _to_str_or_none(voice)
    style = _to_str_or_none(style)
    fmt = _to_str_or_none(fmt)

    try:
        import pyaudio
    except Exception as e:
        typer.secho("PyAudio is required for inline playback.\n"
                    "On Windows: pip install pipwin && pipwin install pyaudio\n"
                    "Else: pip install pyaudio", fg="red")
        raise typer.Exit(code=1)

    # If --stt-input is used, capture spoken prompt using Google STT only
    if stt_input:
        try:
            import speech_recognition as sr
        except ImportError:
            typer.secho("speech_recognition is required for Google STT. Run: pip install SpeechRecognition", fg="red")
            raise typer.Exit(code=1)
        recognizer = sr.Recognizer()
        pause = typer.prompt("Pause threshold (seconds, default 2.5)", default=2.5, type=float)
        recognizer.pause_threshold = pause
        typer.secho(f"Pause threshold set to {pause} seconds.", fg="yellow")
        with sr.Microphone() as source:
            typer.secho("Speak now...", fg="cyan")
            audio = recognizer.listen(source)
        try:
            prompt = recognizer.recognize_google(audio)
            typer.secho(f"Recognized: {prompt}", fg="green")
        except sr.UnknownValueError:
            typer.secho("Could not understand audio.", fg="red")
            raise typer.Exit(code=1)
        except sr.RequestError as e:
            typer.secho(f"Google STT error: {e}", fg="red")
            raise typer.Exit(code=1)
    # ...existing code...
    elif prompt is None:
        typer.secho("Prompt is required unless --stt-input is used.", fg="red")
        raise typer.Exit(code=1)

    # If no voice is provided, try to load last selected voice
    if not voice:
        try:
            with open(VOICE_ID_FILE, encoding='utf-8') as f:
                voice = f.read().strip()
                if voice:
                    typer.secho(f"Using last selected voice ID: {voice}", fg="yellow")
        except Exception:
            pass

    # Auto-detect language from prompt if not set
    detected_lang = extract_lang_from_prompt(prompt) if prompt else None
    lang_to_use = lang or detected_lang
    if detected_lang and not lang:
        typer.secho(f"Detected language from prompt: {detected_lang}", fg="yellow")

    # Auto-detect file names in prompt and search for them recursively in the repo
    file_pattern = re.compile(r"([\w\-\.]+\.py)", re.IGNORECASE)
    found_files = []
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if prompt:
        for match in file_pattern.findall(prompt):
            for root, dirs, filenames in os.walk(repo_root):
                if match in filenames:
                    found_files.append(os.path.abspath(os.path.join(root, match)))
    if found_files:
        # Ensure files is a list before combining
        if not isinstance(files, list) or files is None:
            files = []
        if files:
            files = list(set(files + found_files))
        else:
            files = found_files
        typer.secho(f"Auto-detected files for context: {', '.join(files)}", fg="yellow")

    # (Moved OptionInfo conversion to top of function)
    async def _run():
        # Ensure files is a list of strings
        nonlocal files
        if not isinstance(files, list):
            files = []
        files = [f for f in files if isinstance(f, str)]
        payload = {"text": prompt, "language": lang_to_use, "voice_id": voice,
                   "style": style, "format": fmt, "files": files}
        # Prepare cache key
        file_path = files[0] if files else None
        # Ensure all values are JSON serializable (non-destructive)
        key = make_cache_key(
            _to_str_or_none(prompt),
            _to_str_or_none(lang_to_use),
            _to_str_or_none(file_path),
            _to_str_or_none(voice),
            _to_str_or_none(style),
            _to_str_or_none(fmt)
        )
        if cache_exists(key):
            cached = load_cache(key)
            logging.info(f"Cache hit for key: {key}")
            typer.secho("[CACHE] Loaded transcript and audio from cache.", fg="green")
            if show_transcript:
                print("\n--- Transcript ---\n" + cached["transcript"] + "\n")
            return
        async with websockets.connect(api_ws) as ws:
            await ws.send(json.dumps(payload))
            pa = None
            stream = None
            first = True
            try:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    if "error" in data:
                        logging.error(f"Backend error: {data['error']}")
                        typer.secho("Error: " + data["error"], fg="red")
                        break

                    if "info" in data:
                        info = data["info"]
                        transcript = (info.get("transcript") or "").strip()
                        if transcript:
                            logging.info(f"Received transcript for key: {key}")
                            if show_transcript:
                                print("\n--- Transcript ---\n" + transcript + "\n")
                            cached_transcript = transcript
                        # Initialize audio device
                        pa = pyaudio.PyAudio()
                        stream = pa.open(
                            format=pyaudio.paInt16,  # Murf WS returns 16-bit PCM in WAV container
                            channels=1,
                            rate=int(info.get("sample_rate", 44100)),
                            output=True,
                        )
                        continue

                    if "audio_b64" in data:
                        chunk = base64.b64decode(data["audio_b64"])
                        # Skip the WAV header in the very first chunk
                        if first and len(chunk) > 44:
                            chunk = chunk[44:]
                            first = False
                        if stream:
                            stream.write(chunk)
                                # Optionally, accumulate audio_b64 for caching (not implemented for streaming)
                        continue

                    if data.get("final"):
                        # Save transcript and dummy audio_b64 to cache (real audio caching for streaming is complex)
                        if 'cached_transcript' in locals():
                            save_cache(key, cached_transcript, None, info.get("mime", "audio/wav"))
                            logging.info(f"Saved transcript to cache for key: {key}")
                            typer.secho("[CACHE] Saved transcript to cache.", fg="yellow")
                        break
            finally:
                if stream:
                    stream.stop_stream()
                    stream.close()
                if pa:
                    pa.terminate()

    asyncio.run(_run())

@APP.command(help="List all available Murf voices from voices.json")
def voices(
    voices_path: str = os.path.join(os.path.dirname(__file__), '../local-service/voices.json')
):
    """
    Prints all available voices, their IDs, locales, and styles.
    """
    try:
        with open(voices_path, encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception as e:
        typer.secho(f"Could not load voices.json: {e}", fg="red")
        raise typer.Exit(code=1)

    for locale, voices in catalog.items():
        typer.secho(f"\nLocale: {locale}", fg="cyan")
        for v in voices:
            styles = ', '.join(v.get('styles', []))
            name = v.get('name', v['id'])
            typer.echo(f"  {name} (id: {v['id']}) | Styles: {styles}")

@APP.command(help="Interactively select a Murf voice and print its ID")
def select_voice(
    voices_path: str = os.path.join(os.path.dirname(__file__), '../local-service/voices.json')
):
    """
    Prompts the user to select a voice from voices.json and prints the chosen voice ID. Saves selection for future use.
    """
    try:
        with open(voices_path, encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception as e:
        typer.secho(f"Could not load voices.json: {e}", fg="red")
        raise typer.Exit(code=1)

    all_voices = []
    for locale, voices in catalog.items():
        for v in voices:
            all_voices.append({
                "id": v["id"],
                "name": v.get("name", v["id"]),
                "locale": locale,
                "styles": ', '.join(v.get("styles", []))
            })

    if not all_voices:
        typer.secho("No voices found in voices.json", fg="red")
        raise typer.Exit(code=1)

    typer.echo("Select a voice:")
    for idx, v in enumerate(all_voices, 1):
        typer.echo(f"{idx}. {v['name']} (id: {v['id']}, locale: {v['locale']}, styles: {v['styles']})")
    choice = typer.prompt(f"Enter number (1-{len(all_voices)})", type=int)
    if 1 <= choice <= len(all_voices):
        selected = all_voices[choice-1]
        typer.secho(f"Selected voice ID: {selected['id']}", fg="green")
        # Save to config file
        try:
            with open(VOICE_ID_FILE, 'w', encoding='utf-8') as f:
                f.write(selected['id'])
        except Exception as e:
            typer.secho(f"Could not save voice ID: {e}", fg="red")
    else:
        typer.secho("Invalid selection.", fg="red")
        raise typer.Exit(code=1)


    # ...existing code...

def main():
    APP()

if __name__ == "__main__":
    main()
