# whisper_stt.py
# Speech-to-Text using OpenAI Whisper (non-destructive, can be imported anywhere)
import whisper
import tempfile
import os

def transcribe_audio(audio_path: str, model_size: str = "base") -> str:
    """
    Transcribe an audio file to text using OpenAI Whisper.
    Args:
        audio_path: Path to the audio file (wav, mp3, etc.)
        model_size: Whisper model size (tiny, base, small, medium, large)
    Returns:
        Transcribed text as a string.
    """
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    return result["text"].strip()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python whisper_stt.py <audiofile>")
        sys.exit(1)
    text = transcribe_audio(sys.argv[1])
    print("Transcription:", text)
