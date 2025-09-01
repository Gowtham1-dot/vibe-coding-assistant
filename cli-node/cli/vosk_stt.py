# vosk_stt.py
# Simple Vosk STT utility for live_agent integration
import sounddevice as sd
import queue
import vosk
import json
import os

def transcribe_vosk(duration=5, lang_model_path=None, samplerate=16000):
    """
    Record audio from the microphone and transcribe using Vosk.
    duration: seconds to record
    lang_model_path: path to Vosk model directory (download from https://alphacephei.com/vosk/models)
    samplerate: audio sample rate
    Returns: transcribed text
    """
    if lang_model_path is None:
        lang_model_path = os.environ.get("VOSK_MODEL", "vosk-model-small-en-us-0.15")
    # Always resolve model path to project root
    lang_model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vosk-model-small-en-us-0.15'))
    if not os.path.isdir(lang_model_path):
        raise RuntimeError(f"Vosk model not found at {lang_model_path}. Download from https://alphacephei.com/vosk/models and unzip.")
    model = vosk.Model(lang_model_path)
    q = queue.Queue()
    def callback(indata, frames, time, status):
        q.put(bytes(indata))
    with sd.RawInputStream(samplerate=samplerate, blocksize = 8000, dtype='int16', channels=1, callback=callback):
        print(f"Recording for {duration} seconds...")
        rec = vosk.KaldiRecognizer(model, samplerate)
        for _ in range(0, int(samplerate / 8000 * duration)):
            data = q.get()
            if rec.AcceptWaveform(data):
                pass
        result = rec.FinalResult()
    text = json.loads(result).get("text", "").strip()
    print("You said:", text)
    return text

if __name__ == "__main__":
    print(transcribe_vosk())
