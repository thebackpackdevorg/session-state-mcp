# session-state-mcp

MCP server for saving and resuming Claude session states. Close a session and resume it later with a clean context window but all the relevant information intact.

## The problem

- Multiple Claude sessions running in parallel → hard to find and resume a specific one
- Long sessions accumulate context → `/compact` degrades quality
- Starting fresh is more efficient, but you lose the thread

## The solution

Save your session state before closing. Resume in a new clean session with full context.

```
# End of session
"save this state as gym-tracker-release"

# New session, next day
"load state gym-tracker-release"
```

---

## Tools

| Tool | Description |
|------|-------------|
| `save_state` | Save current session state to disk |
| `list_states` | List all saved states (most recent first) |
| `load_state` | Load a state by name to resume work |
| `delete_state` | Delete a state by name |
| `session_state_guide` | Full usage guide and tips |

---

## Installation

### 1. Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

### 2. Clone or download the server

```bash
git clone <repo-url> ~/session-state-mcp
# or just copy server.py to any directory
```

### 3. Test that the server starts

```bash
cd ~/session-state-mcp
uv run server.py
```

You should see the FastMCP banner and `Starting MCP server`. Press `Ctrl+C` to stop.

### 4. Register in Claude Code

Add the following entry to `~/.claude.json` under `mcpServers`:

```json
"session-state-mcp": {
  "type": "stdio",
  "command": "/path/to/uv",
  "args": ["run", "/path/to/session-state-mcp/server.py"]
}
```

Find the full path to `uv` with:

```bash
which uv
```

**Example** (Linux/WSL with uv installed in home):

```json
"session-state-mcp": {
  "type": "stdio",
  "command": "/home/youruser/.local/bin/uv",
  "args": ["run", "/home/youruser/session-state-mcp/server.py"]
}
```

### 5. Restart Claude Code

The new MCP server will be available in your next session. States are stored in `~/.claude-states/` (created automatically on first use).

---

## Usage

### Save a state

At the end of a session, tell Claude:

> "save this state as `<name>`"

Claude will populate summary, decisions, pending tasks, files touched, and work mode from the conversation.

### Resume a state

In a new session:

> "load state `<name>`"

Claude receives the full handoff context and can continue immediately.

### Browse saved states

> "list my saved states"

Shows all states with date, work mode, and summary preview.

### Partial name matching

`load_state` and `delete_state` support partial matches — `"load state gym"` finds `"gym-tracker-release"` if it's the only match.

---

## Tips

- **Name with kebab-case slugs** that describe the work, not the date. The date is saved automatically.  
  Good: `subwatch-auth-spec` · Bad: `session-april-8`

- **Summary is the most important field.** Write it as a handoff note: what was decided, what's blocked, what the next action is.

- **Save before `/compact`.** If a session is getting long, save state first so you can start fresh instead of compacting.

- **Overwrite is safe.** Saving a state with an existing name overwrites it — use this to update state mid-session.

- **One state per topic.** If you're working on two unrelated things in the same session, save two separate states.

---

## Storage

States are saved as human-readable JSON files in `~/.claude-states/`:

```json
{
  "name": "gym-tracker-release",
  "slug": "gym-tracker-release",
  "created_at": "2026-04-08T10:00:00",
  "summary": "Prepared v1.2 release. APK signed and uploaded to Play Store...",
  "decisions": ["Bumped version to 1.2.0", "Kept legacy weight unit support"],
  "pending": ["Wait for Play Store review", "Post release notes"],
  "files_touched": ["app/build.gradle", "CHANGELOG.md"],
  "work_mode": "quick-execution"
}
```
