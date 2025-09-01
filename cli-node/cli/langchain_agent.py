# langchain_agent.py
# Free, local LangChain agent for code Q&A and editing
# Uses HuggingFace Transformers (local LLM), Vosk STT, and Murf TTS (free tier)

import os
from langchain.llms import HuggingFacePipeline
from transformers import pipeline
from vosk_stt import transcribe_vosk
from vibe_stream import stream as murf_stream

# Load a local HuggingFace model (e.g., distilgpt2 for demo)
def get_local_llm():
    pipe = pipeline("text-generation", model="distilgpt2")
    return HuggingFacePipeline(pipeline=pipe)

# Simple agent: answer code questions using local LLM
def answer_code_question(question, file_path=None):
    llm = get_local_llm()
    context = ""
    if file_path and os.path.isfile(file_path):
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            context = f.read(2000)
    prompt = f"Question: {question}\nContext:\n{context}\nAnswer:"
    return llm(prompt)

# Voice-driven Q&A
def voice_code_qa():
    print("Say your code question (offline STT)...")
    question = transcribe_vosk(duration=5)
    print(f"You asked: {question}")
    # For demo, just use app.py in local-service
    answer = answer_code_question(question, file_path=os.path.join("..", "local-service", "app.py"))
    print("Answer:", answer)
    # Speak answer with Murf TTS (if available)
    murf_stream(prompt=answer, lang="en", stt_input=False)

if __name__ == "__main__":
    voice_code_qa()
