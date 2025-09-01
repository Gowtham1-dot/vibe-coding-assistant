# langchain_advanced_agent.py
# Advanced LangChain agent for Murf API hackathon
# Adds new features: code editing, repo Q&A, voice-driven workflows
# Does NOT modify or break any existing code

import os
from langchain_community.llms import HuggingFacePipeline
from transformers import pipeline
from vosk_stt import transcribe_vosk
from vibe_stream import stream as murf_stream

# Load a local HuggingFace model (e.g., distilgpt2 for demo)
def get_local_llm():
    pipe = pipeline("text-generation", model="distilgpt2")
    return HuggingFacePipeline(pipeline=pipe)

# Advanced agent: supports Q&A, code editing, and file creation
def agent_action(action, target_file=None, code_snippet=None):
    llm = get_local_llm()
    result = ""
    if action == "summarize":
        context = ""
        if target_file and os.path.isfile(target_file):
            with open(target_file, encoding="utf-8", errors="ignore") as f:
                context = f.read(2000)
        prompt = f"Summarize the following code:\n{context}\nSummary:"
        result = llm(prompt)
    elif action == "add_code" and target_file and code_snippet:
        # Add code snippet to file (append, never overwrite)
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(f"\n# Added by LangChain agent\n{code_snippet}\n")
        result = f"Code added to {target_file}."
    elif action == "refactor" and target_file:
        # Generate refactored code (does not overwrite)
        with open(target_file, encoding="utf-8", errors="ignore") as f:
            context = f.read(2000)
        prompt = f"Refactor the following code for best practices:\n{context}\nRefactored code:"
        result = llm(prompt)
    else:
        result = "Unknown action or missing parameters."
    return result

# Voice-driven workflow
def voice_agent():
    command = input("Type your agent command (e.g., 'summarize app.py', 'add function to app.py'): ")
    # Simple parser for demo (revert to app.py only)
    if "summarize" in command:
        result = agent_action("summarize", target_file=os.path.join("..", "local-service", "app.py"))
    elif "add function" in command:
        code_snippet = "def new_function():\n    print('Hello from LangChain agent!')"
        result = agent_action("add_code", target_file=os.path.join("..", "local-service", "app.py"), code_snippet=code_snippet)
    elif "refactor" in command:
        result = agent_action("refactor", target_file=os.path.join("..", "local-service", "app.py"))
    else:
        result = "Command not recognized. Try 'summarize', 'add function', or 'refactor'."
    print("Agent result:", result)
    murf_stream(prompt=result, lang="en", stt_input=False)

if __name__ == "__main__":
    voice_agent()
