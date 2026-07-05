from .claude_code import list_sessions as list_claude, resume_command as resume_claude
from .codex import list_sessions as list_codex, resume_command as resume_codex
from .gemini import list_sessions as list_gemini, resume_command as resume_gemini

PROVIDERS = {
    "claude": {
        "list": list_claude,
        "resume": resume_claude,
    },
    "codex": {
        "list": list_codex,
        "resume": resume_codex,
    },
    "gemini": {
        "list": list_gemini,
        "resume": resume_gemini,
    },
}
