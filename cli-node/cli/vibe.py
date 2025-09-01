# cli/vibe.py
import os, sys, base64, tempfile, requests, typer
from typing import List, Optional
import sys
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import  json,  asyncio, websockets, pyaudio



APP = typer.Typer(no_args_is_help=True, add_completion=False)
@APP.command(help="Stream TTS (no external player).")
def stream(
    prompt: str,
    lang: Optional[str] = typer.Option(None, "--lang", "-l"),
    api_ws: str = typer.Option("ws://127.0.0.1:8001/ws/stream", "--api-ws"),
    voice: Optional[str] = typer.Option(None, "--voice-id"),
    style: Optional[str] = typer.Option(None, "--style"),
    fmt: str = typer.Option("WAV", "--format"),
    files: List[str] = typer.Option(None, "--file", "-f"),
):
    async def _run():
        payload = {"text": prompt, "language": lang, "voice_id": voice, "style": style, "format": fmt, "files": files}
        async with websockets.connect(api_ws) as ws:
            await ws.send(json.dumps(payload))
            pa = None
            stream = None
            first_chunk = True
            try:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if "error" in data:
                        typer.secho("Error: " + data["error"], fg="red")
                        break
                    if "info" in data:
                        info = data["info"]
                        print("\n--- Transcript ---\n" + info.get("transcript","").strip() + "\n")
                        # init audio device
                        pa = pyaudio.PyAudio()
                        stream = pa.open(
                            format=pyaudio.paInt16,  # Murf WS returns 16-bit PCM in WAV container
                            channels=1, rate=int(info.get("sample_rate", 44100)), output=True
                        )
                        continue
                    if "audio_b64" in data:
                        chunk = base64.b64decode(data["audio_b64"])
                        # skip WAV header on the very first frame
                        if first_chunk and len(chunk) > 44:
                            chunk = chunk[44:]
                            first_chunk = False
                        if stream:
                            stream.write(chunk)
                        continue
                    if data.get("final"):
                        break
            finally:
                if stream:
                    stream.stop_stream()
                    stream.close()
                if pa:
                    pa.terminate()

    asyncio.run(_run())

def _abs_existing(paths: Optional[List[str]]) -> Optional[List[str]]:
    if not paths:
        return None
    out = []
    for p in paths:
        ap = os.path.abspath(p)
        if os.path.exists(ap):
            out.append(ap)
    return out or None

def _play_inline_windows_wav(wav_bytes: bytes) -> bool:
    """Play WAV from memory on Windows, synchronously. Returns True if played."""
    if not sys.platform.startswith("win"):
        return False
    try:
        import winsound  # stdlib on Windows
        # Synchronous playback (no external player)
        winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
        return True
    except Exception:
        return False

@APP.command(help="Send a prompt and speak the answer inline (no external player).")
def main(
    prompt: str = typer.Argument(..., help="Your prompt"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Language code (en, es, te, …)"),
    api: str = typer.Option(os.getenv("VIBE_API", "http://127.0.0.1:8001/speak"), "--api", help="Service endpoint"),
    voice: Optional[str] = typer.Option(None, "--voice-id", help="TTS voice id (e.g., Murf voice)"),
    fmt: str = typer.Option("wav", "--format", help="wav or mp3 (wav enables inline playback on Windows)"),
    style: Optional[str] = typer.Option(None, "--style", help="Optional TTS style"),
    files: List[str] = typer.Option(None, "--file", "-f", help="File(s) to include as context", show_default=False),
    save: Optional[str] = typer.Option(None, "--save", help="Optional path to save audio"),
):
    payload = {"text": prompt, "format": fmt}
    if lang:  payload["language"] = lang
    if voice: payload["voice_id"] = voice
    if style: payload["style"] = style
    abs_files = _abs_existing(files)
    if abs_files:
        payload["files"] = abs_files

    r = requests.post(api, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()

    text = (data.get("text") or "").strip()
    b64  = data.get("audio_b64")
    mime = (data.get("mime") or "").lower()

    # 1) show transcript
    if text:
        print("\n--- Transcript ---\n" + text + "\n")

    if not b64:
        typer.secho("No audio in response.", fg="red")
        raise typer.Exit(code=1)

    audio_bytes = base64.b64decode(b64)

    # 2) inline playback (Windows + WAV only)
    is_wav = ("wav" in mime) or (fmt.lower() == "wav")
    if is_wav and sys.platform.startswith("win"):
        played = _play_inline_windows_wav(audio_bytes)
        if played:
            if save:
                with open(save, "wb") as f:
                    f.write(audio_bytes)
                print(f"(Saved: {os.path.abspath(save)})")
            return
        else:
            typer.secho("Inline WAV playback failed, falling back to saving a file.", fg="yellow")

    # 3) fallback: save to file (no external app launched)
    if save:
        out = save
    else:
        ext = ".wav" if is_wav else ".mp3"
        out = tempfile.NamedTemporaryFile(suffix=ext, delete=False).name

    with open(out, "wb") as f:
        f.write(audio_bytes)

    print(f"Saved: {os.path.abspath(out)}")
    if not is_wav and sys.platform.startswith("win"):
        print("Tip: use --format wav for instant inline playback on Windows.")
    elif not sys.platform.startswith("win"):
        print("Tip: inline playback is implemented for Windows only. Saved instead.")

def main():
    APP()

if __name__ == "__main__":
    main()
