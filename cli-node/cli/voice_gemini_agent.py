# voice_gemini_agent.py
# Voice-driven agent using Vosk STT for input and Gemini+Murf backend for output
# Sends voice command to FastAPI backend and plays Murf TTS response


import os
import requests
import tempfile
import speech_recognition as sr
import base64

BACKEND_URL = os.environ.get("VIBE_BACKEND_URL", "http://localhost:8000/speak")

def listen_google():
    recognizer = sr.Recognizer()
    user_input = input("Type 's' to speak, 'q' to quit, or Enter to skip: ").strip().lower()
    if user_input == "q":
        return None
    if user_input != "s":
        return None
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1.0
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

def play_audio(audio_path):
    if os.name == "nt":
        os.system(f'start /min wmplayer "{audio_path}"')
    else:
        os.system(f'ffplay -nodisp -autoexit "{audio_path}"')

def main():
    print("Type 's' to speak your command, 'q' to quit.")
    while True:
        command_text = listen_google()
        if not command_text:
            print("No command received. Exiting.")
            break
        payload = {"text": command_text, "language": "en"}
        try:
            resp = requests.post(BACKEND_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            print(f"Gemini response: {data.get('text')}")
            audio_b64 = data.get("audio_b64")
            mime = data.get("mime", "audio/wav")
            if audio_b64:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav" if "wav" in mime else ".mp3") as f:
                    f.write(base64.b64decode(audio_b64))
                    audio_path = f.name
                play_audio(audio_path)
            else:
                print("No audio returned from backend.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
