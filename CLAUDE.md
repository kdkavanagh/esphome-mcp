# CLAUDE.md

## Project Overview
ESPHome MCP Server — a Python MCP server exposing read-only tools for interacting with an ESPHome dashboard via its web API.

## Tech Stack
- **MCP framework**: `fastmcp` (v3.1.1+)
- **HTTP client**: `httpx` (async)
- **WebSocket**: `websockets` (for log streaming)
- **Config**: `pydantic-settings` (env var parsing)
- **Build**: `hatchling`
- **Linting/formatting**: `ruff`
- **Type checking**: `ty`
- **Testing**: `pytest` + `pytest-asyncio`

## Project Structure
```
src/esphome_mcp/
├── __init__.py
├── __main__.py      # Entry point: calls mcp.run()
├── server.py        # FastMCP instance + 4 tool definitions
└── client.py        # ESPHome dashboard HTTP/WS client + settings
tests/
├── conftest.py      # Fixtures: real ESPHome dashboard + MCP client
└── test_tools.py    # Integration tests for all tools
```

## Key Architecture Decisions
- **Client uses lazy init, not a singleton**: `get_client()` creates the client on first access. Tests call `configure(settings)` to override the URL, then `reset()` on teardown. Never mock the client.
- **Tools return error strings, never raise**: MCP tools should always return useful text to the LLM, even on failure.
- **All tools are read-only**: Annotated with `readOnlyHint=True`.

## Development Commands
```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install ruff ty pytest pytest-asyncio esphome

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type check
ty check src/

# Run tests (spins up a real ESPHome dashboard)
pytest tests/ -v
```

## Environment Variables
- `ESPHOME_DASHBOARD_URL` (required) — e.g. `http://192.168.1.100:6052`
- `ESPHOME_DASHBOARD_USERNAME` (optional) — Basic Auth username
- `ESPHOME_DASHBOARD_PASSWORD` (optional) — Basic Auth password

## Testing Approach
Tests are **integration tests** — they start a real ESPHome dashboard subprocess with dummy device configs and test the full stack (MCP protocol → tools → HTTP client → dashboard). No mocking. Test device configs are realistic ESPHome YAML (ESP8266 power monitor, ESP32 sensor hub).

## ESPHome Dashboard API Endpoints Used
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /devices` | HTTP | List configured devices |
| `GET /version` | HTTP | Get ESPHome version |
| `GET /edit?configuration=<file>` | HTTP | Read YAML config |
| `WS /logs` | WebSocket | Stream device logs |
