# voice_github_agent.py
# Voice-driven GitHub agent: create/list issues by voice, Murf TTS for output
# Requires: requests, speech_recognition, Murf backend, GitHub token in .env

import os
import requests
import speech_recognition as sr
from vibe_stream import stream as murf_stream

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "owner/repo")  # e.g., "octocat/Hello-World"
GITHUB_API = "https://api.github.com"
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}



def get_command():
    cmd = input("Type your GitHub command (or 'q' to quit): ").strip()
    if cmd.lower() == 'q':
        return None
    return cmd


def create_issue(title):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues"
    resp = requests.post(url, headers=HEADERS, json={"title": title})
    if resp.status_code == 201:
        return f"Issue created: {title}"
    else:
        return f"Failed to create issue: {resp.text}"


def list_issues():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        issues = resp.json()
        if not issues:
            return "No open issues."
        return "Open issues:\n" + "\n".join(f"#{i['number']}: {i['title']}" for i in issues)
    else:
        return f"Failed to list issues: {resp.text}"


def parse_intent(text):
    text = text.lower()
    import re
    # Support more natural language for creating issues
    create_patterns = [
        r"create issue[:]? (.+)",
        r"create (?:me |an |a )?(?:issue )?(.+)",
        r"open issue (?:about |on |for )?(.+)",
        r"add (?:an |a )?(?:issue |bug |feature )?(.+)",
        r"report (?:an |a )?(?:issue |bug )?(.+)",
        r"file (?:an |a )?(?:issue |bug )?(.+)"
    ]
    for pat in create_patterns:
        m = re.search(pat, text)
        if m:
            title = m.group(1).strip('"')
            return "create", title
    if "list issues" in text or "show issues" in text or "open issues" in text:
        return "list", None
    return None, None


def main():
    print("Type your GitHub command (or 'q' to quit).")
    while True:
        command_text = get_command()
        if not command_text:
            print("No command received. Exiting.")
            break
        intent, arg = parse_intent(command_text)
        if intent == "create" and arg:
            result = create_issue(arg)
        elif intent == "list":
            result = list_issues()
        else:
            result = "Command not recognized. Try: 'create issue <title>' or 'list issues'."
        print(result)
        murf_stream(prompt=result, lang="en", stt_input=False)

if __name__ == "__main__":
    main()
