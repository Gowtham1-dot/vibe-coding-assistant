# voice_git_agent.py
# Voice-driven git agent using Vosk STT for input and Murf TTS for output
# User-friendly, non-destructive, only runs safe git commands


import os
import subprocess
import speech_recognition as sr
from vibe_stream import stream as murf_stream

def run_git_command(command):
    try:
        result = subprocess.check_output(command, shell=True, encoding='utf-8', stderr=subprocess.STDOUT)
        return result.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e.output.strip()}"

def parse_intent(text):
    text = text.lower()
    if "status" in text:
        return ["git status"], "Showing git status."
    if "commit" in text:
        import re
        msg = re.search(r"commit.*?['\"](.+?)['\"]", text)
        if msg:
            return [f"git commit -am \"{msg.group(1)}\""], f"Committing changes with message: {msg.group(1)}"
        else:
            return None, "Please specify a commit message in quotes."
    if "branch" in text and "create" in text:
        import re
        br = re.search(r"branch.*?create.*?(\w+)", text)
        if br:
            return [f"git checkout -b {br.group(1)}"], f"Creating and switching to branch: {br.group(1)}"
        else:
            return None, "Please specify a branch name."
    if "show last commit" in text:
        return ["git log -1"], "Showing last commit."
    if "push" in text:
        return ["git push"], "Pushing changes to origin."
    return None, "Command not recognized. Try: status, commit, create branch, show last commit, push."

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

def main():
    print("Type 's' to speak your git command, 'q' to quit.")
    while True:
        command_text = listen_google()
        if not command_text:
            print("No command received. Exiting.")
            break
        commands, feedback = parse_intent(command_text)
        if not commands:
            print(feedback)
            murf_stream(prompt=feedback, lang="en", stt_input=False)
            continue
        results = []
        for cmd in commands:
            print(f"Running: {cmd}")
            res = run_git_command(cmd)
            results.append(res)
        output = feedback + "\n" + "\n".join(results)
        print(output)
        murf_stream(prompt=output, lang="en", stt_input=False)

if __name__ == "__main__":
    main()
