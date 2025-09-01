
# vibe-coding-assistant
=======
# Vibe-Coding-Assistant: Multilingual Voice-Driven Coding Assistant

Vibe-Coding-Assistant is a multilingual, voice-driven coding assistant that integrates Murf TTS, Google SpeechRecognition, and LLM APIs to provide a seamless, hands-free coding and learning experience in your preferred language. It includes a single main agent (`live_agent.py`) for interactive, multilingual voice-driven workflows, a local Murf/Gemini backend, and a planned VS Code extension for code narration in multiple languages.

---

## Table of Contents
- [Project Structure](#project-structure)
- [Features](#features)
- [Setup & Installation](#setup--installation)
- [How to Use](#how-to-use)
- [File-by-File Explanation](#file-by-file-explanation)
- [VS Code Extension (Future)](#vs-code-extension-future)
- [LangChain Agents (Future)](#langchain-agents-future)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## Project Structure

```
Vibe-Coding-Assistant/
├── cli/
│   ├── cache_utils.py
│   ├── vibe_stream.py
│   ├── live_agent.py
│   └── ...
├── local-service/
│   ├── app.py
│   ├── tts.py
│   ├── murf_client.py
│   └── ...
├── vscode-extension/ (future)
├── README.md
├── pyproject.toml
├── package.json
└── ...
```

---

## Features
- **Multilingual live voice agent:** Interactive, voice-driven coding assistant for explanations, code walkthroughs, and more, in your chosen language (supports English, Hindi, Spanish, French, German, Tamil, and more via Murf TTS).
- **Murf TTS integration:** All feedback is spoken aloud in your selected language and voice.
- **Google SpeechRecognition:** For voice input in multiple languages.
- **Local FastAPI backend:** Streams TTS and LLM responses in any supported language.
- **VS Code extension (future):** Narrate code/comments in the editor in your preferred language.
- **LangChain agents (future):** Advanced LLM workflows.

---

## Setup & Installation

1. **Clone the repo:**
   ```sh
   git clone https://github.com/<your-username>/Vibe-Coding-Assistant.git
   cd Vibe-Coding-Assistant
   ```
2. **Install Python dependencies:**
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r local-service/requirements.txt
   pip install -r cli/requirements.txt  # if present
   ```
3. **Install Node dependencies (for VS Code extension):**
   ```sh
   cd vscode-extension
   npm install
   cd ..
   ```
4. **Set up environment variables:**
   - Copy `.env.example` to `.env` and fill in your API keys (Murf, Gemini, etc.).
   - Example for `local-service/.env`:
     ```env
     MURF_API_KEY=your_murf_api_key
     GEMINI_API_KEY=your_gemini_api_key
     ```
5. **Start the local backend:**
   ```sh
   cd local-service
   uvicorn app:app --reload
   ```

---

## How to Use

### Live Agent (Multilingual)
- Run: `python cli/live_agent.py`
- Speak your coding questions, requests for explanations, or walkthroughs in your preferred language.
- The agent will respond with spoken feedback using Murf TTS in the same or another language.
- You can specify the language for both input and output (see Murf TTS and Google SpeechRecognition docs for supported languages).

#### Example Commands
- **English:**
  - "Explain the function in app.py"
  - "How do I create a virtual environment in Python?"
- **Hindi:**
  - "app.py में यह फंक्शन क्या करता है?"
- **Spanish:**
  - "Explica el código en app.py"
- **French:**
  - "Explique la fonction principale du script"
- **Change output language:**
  - Use the `--lang` option: `python cli/vibe_stream.py stream "explain app.py" --lang fr-FR`

### TTS Streaming (Multilingual)
- Use `vibe_stream.py` to stream TTS for any prompt in any supported language:
  ```sh
  python cli/vibe_stream.py stream "explain app.py" --lang hi-IN
  ```

---

## File-by-File Explanation

### CLI Folder (`cli/`)
- **cache_utils.py:** Handles caching of TTS results for faster replay.
- **vibe_stream.py:** Core streaming logic for TTS, including Murf API, caching, and playback. Supports multilingual TTS and STT.
- **live_agent.py:** The main, interactive, multilingual voice-driven agent for coding help and explanations.
- **vosk_stt.py, whisper_stt.py:** (Optional) Alternative STT backends for different languages.

### Local Service (`local-service/`)
- **app.py:** FastAPI backend for TTS and LLM streaming. Relays requests to Murf and Gemini APIs, supporting multiple languages.
- **tts.py:** Handles TTS requests and Murf API integration for all supported languages.
- **murf_client.py:** Low-level Murf API client.
- **voices.json:** List of available Murf voices and languages.

### VS Code Extension (`vscode-extension/`) (Future)
- **package.json, src/:** VS Code extension to narrate selected code/comments using Murf TTS in any supported language. (Coming soon)

### LangChain Agents (Future)
- **(Planned):** LangChain-based agents for advanced LLM workflows and conversational coding in multiple languages. Not included in this version.

### Project Root
- **README.md:** This file.
- **pyproject.toml:** Python project metadata and CLI entry points.
- **package.json:** Node project metadata (for VS Code extension).

---

## Troubleshooting
- **Murf TTS not working:** Check your API key and backend URL.
- **Audio not playing:** Ensure PyAudio is installed and your system audio is working.
- **.env issues:** Double-check all environment variables are set and loaded.
- **Language not supported:** Check Murf and Google SpeechRecognition docs for supported language codes.

---

## Contributing
- Pull requests and suggestions are welcome!
- See `cli/test_vibe_stream.py` for how to add tests.
- For feature requests, open an issue on GitHub.

---

## Use Cases
- Hands-free, multilingual coding and code explanations.
- Narrating code, comments, or documentation in VS Code (future) in your native language.
- Educational coding assistant for students and teams in any supported language.

---

## License
MIT
>>>>>>> 9c25975 (Initial multilingual voice assistant commit)

