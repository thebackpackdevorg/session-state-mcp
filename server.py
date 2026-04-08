# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastmcp>=2.0",
# ]
# ///

from fastmcp import FastMCP
import json
import re
from pathlib import Path
from datetime import datetime

mcp = FastMCP("session-state-mcp")

STATES_DIR = Path.home() / ".claude-states"
STATES_DIR.mkdir(exist_ok=True)


def _name_to_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _parse_list(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except (json.JSONDecodeError, TypeError):
        return [value] if value else []


def _find_state_file(name: str) -> Path | None:
    slug = _name_to_slug(name)
    direct = STATES_DIR / f"{slug}.json"
    if direct.exists():
        return direct
    matches = sorted(STATES_DIR.glob(f"*{slug}*.json"))
    return matches[0] if matches else None


@mcp.tool()
def save_state(
    name: str,
    summary: str,
    decisions: str | list[str] | None = None,
    pending: str | list[str] | None = None,
    files_touched: str | list[str] | None = None,
    work_mode: str = "",
) -> str:
    """
    Save the current session state to disk so it can be resumed in a future session.

    Args:
        name: Short descriptive name for this state (e.g. "gym-tracker-release-prep")
        summary: What was done and where things stand — write this as a handoff note
        decisions: Key decisions made during this session
        pending: Tasks that still need to be done
        files_touched: File paths that are relevant to this work
        work_mode: Working mode (e.g. "spec-driven", "quick-execution", "discovery")
    """
    slug = _name_to_slug(name)
    file_path = STATES_DIR / f"{slug}.json"
    overwrite = file_path.exists()

    state = {
        "name": name,
        "slug": slug,
        "created_at": datetime.now().isoformat(),
        "summary": summary,
        "decisions": _parse_list(decisions),
        "pending": _parse_list(pending),
        "files_touched": _parse_list(files_touched),
        "work_mode": work_mode,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    action = "updated" if overwrite else "saved"
    return f"State '{name}' {action}.\nFile: {file_path}"


@mcp.tool()
def list_states() -> str:
    """List all saved session states, sorted by most recent first."""
    files = sorted(
        STATES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )

    if not files:
        return "No saved states found."

    lines = ["## Saved States\n"]
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                state = json.load(fh)
            date = state.get("created_at", "")[:10]
            name = state.get("name", f.stem)
            summary = state.get("summary", "")
            short = summary[:120] + "..." if len(summary) > 120 else summary
            pending_count = len(state.get("pending", []))
            mode = state.get("work_mode", "")
            meta = f"[{mode}]" if mode else ""
            lines.append(f"**{name}** {meta} — {date}")
            lines.append(short)
            if pending_count:
                lines.append(f"_{pending_count} pending task(s)_")
            lines.append("")
        except Exception:
            lines.append(f"- {f.stem} (could not read)")

    return "\n".join(lines)


@mcp.tool()
def load_state(name: str) -> str:
    """
    Load a saved session state by name to resume work in a new session.
    Returns the full state as a structured handoff context.

    Args:
        name: Name or partial name of the state to load
    """
    file_path = _find_state_file(name)
    if not file_path:
        available = [f.stem for f in STATES_DIR.glob("*.json")]
        hint = f"\nAvailable: {', '.join(available)}" if available else ""
        return f"State '{name}' not found.{hint}"

    with open(file_path, encoding="utf-8") as f:
        state = json.load(f)

    lines = [
        f"# Session State: {state['name']}",
        f"**Saved:** {state.get('created_at', '')[:19].replace('T', ' ')}",
    ]
    if state.get("work_mode"):
        lines.append(f"**Mode:** {state['work_mode']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(state.get("summary", ""))

    if state.get("decisions"):
        lines.append("\n## Decisions")
        for d in state["decisions"]:
            lines.append(f"- {d}")

    if state.get("pending"):
        lines.append("\n## Pending Tasks")
        for t in state["pending"]:
            lines.append(f"- [ ] {t}")

    if state.get("files_touched"):
        lines.append("\n## Files Touched")
        for rf in state["files_touched"]:
            lines.append(f"- `{rf}`")

    return "\n".join(lines)


@mcp.tool()
def delete_state(name: str) -> str:
    """
    Delete a saved session state by name.

    Args:
        name: Name or partial name of the state to delete
    """
    file_path = _find_state_file(name)
    if not file_path:
        return f"State '{name}' not found."

    state_name = json.loads(file_path.read_text(encoding="utf-8")).get("name", name)
    file_path.unlink()
    return f"State '{state_name}' deleted."


@mcp.tool()
def session_state_guide() -> str:
    """
    Returns documentation, usage patterns, and tips for the session-state-mcp server.
    Call this to understand how to use the server effectively.
    """
    return """
# Session State MCP — Guide

Saves and restores Claude session context so you can close a session and resume
it later with a clean context window but all the relevant information.

---

## Tools

| Tool | Description |
|------|-------------|
| `save_state` | Save current session state to disk |
| `list_states` | List all saved states (most recent first) |
| `load_state` | Load a state by name to resume work |
| `delete_state` | Delete a state by name |
| `session_state_guide` | This guide |

---

## save_state — parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Short slug-friendly name (e.g. "gym-tracker-release") |
| `summary` | str | yes | Handoff note — what was done, where things stand |
| `decisions` | list[str] | no | Key decisions made this session |
| `pending` | list[str] | no | Tasks still to be done |
| `files_touched` | list[str] | no | Relevant file paths |
| `work_mode` | str | no | e.g. "spec-driven", "quick-execution", "discovery" |

---

## Usage patterns

### Saving a state at end of session
Tell Claude: "save this state as <name>"
Claude will populate all fields from the conversation context.

### Resuming in a new session
1. Open a new Claude Code session (clean context)
2. Say: "load state <name>"
3. Claude receives the full handoff and can continue immediately

### Browsing saved sessions
Say: "list my saved states" — shows all states with date and summary preview.

### Partial name matching
`load_state` and `delete_state` support partial matches.
"load state gym" will find "gym-tracker-release" if it's the only match.

---

## Tips

- **Name convention**: use kebab-case slugs that describe the work, not the date
  (the date is saved automatically). Good: "subwatch-auth-spec". Bad: "session-april-8".

- **Summary is the most important field**: write it as a handoff note to your
  future self. Include what was decided, what's blocked, and what the next
  action is.

- **Save before /compact**: if a session is getting long and you're about to
  compact, save state first so you can always start fresh instead.

- **One state per topic**: if you're working on two unrelated things in the same
  session, save two separate states with different names.

- **Overwrite is safe**: saving a state with an existing name overwrites it.
  Use this to update state mid-session as things evolve.

---

## Storage

States are saved as JSON files in `~/.claude-states/`.
Each file is named `<slug>.json` and is human-readable.
"""


if __name__ == "__main__":
    mcp.run()
