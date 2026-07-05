import os
import json
from pathlib import Path


def get_storage_path():
    return os.path.expanduser("~/.gemini/sessions.jsonl")


def parse_sessions(file_path):
    sessions = []
    if not os.path.exists(file_path):
        return sessions
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    sessions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return sessions


def list_sessions():
    path = get_storage_path()
    sessions = parse_sessions(path)
    result = []
    for s in sessions:
        result.append({
            "id": s.get("session_id", ""),
            "name": s.get("title", ""),
            "timestamp": s.get("updated_at", ""),
            "source": "gemini",
        })
    return result


def resume_command(session_id):
    return f"gemini resume {session_id}"
