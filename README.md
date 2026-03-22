# ESPHome MCP Server

An MCP (Model Context Protocol) server for interacting with an [ESPHome](https://esphome.io) dashboard. Provides read-only tools to list devices, check for updates, view configurations, and stream logs.

## Tools

| Tool | Description |
|------|-------------|
| `list_devices` | List all configured devices with versions, addresses, status, and platform info |
| `list_device_names` | List only the names of all configured devices |
| `check_device_update` | Check if a firmware update is available for a specific device |
| `get_device_status` | Check whether a device is online or offline |
| `get_device_configuration` | View the YAML configuration file for a device |
| `get_device_logs` | Stream and collect logs from a device (configurable duration, max 30s) |

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## Configuration

Set the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `ESPHOME_DASHBOARD_URL` | Yes | Base URL of your ESPHome dashboard (e.g., `http://192.168.1.100:6052`) |
| `ESPHOME_DASHBOARD_USERNAME` | No | Username for Basic Auth (if dashboard auth is enabled) |
| `ESPHOME_DASHBOARD_PASSWORD` | No | Password for Basic Auth (if dashboard auth is enabled) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`) |

## Usage

### Standalone

```bash
export ESPHOME_DASHBOARD_URL=http://192.168.1.100:6052
esphome-mcp
```

### Claude Desktop

Add to your Claude Desktop MCP configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "esphome": {
      "command": "esphome-mcp",
      "env": {
        "ESPHOME_DASHBOARD_URL": "http://192.168.1.100:6052"
      }
    }
  }
}
```

### With authentication

```json
{
  "mcpServers": {
    "esphome": {
      "command": "esphome-mcp",
      "env": {
        "ESPHOME_DASHBOARD_URL": "http://192.168.1.100:6052",
        "ESPHOME_DASHBOARD_USERNAME": "admin",
        "ESPHOME_DASHBOARD_PASSWORD": "your-password"
      }
    }
  }
}
```

### Claude Code

Add a `.claude/settings.json` to your project to auto-approve the read-only tools exposed by this server:

```json
{
  "permissions": {
    "allow": [
      "mcp__esphome__list_devices",
      "mcp__esphome__list_device_names",
      "mcp__esphome__check_device_update",
      "mcp__esphome__get_device_status",
      "mcp__esphome__get_device_configuration",
      "mcp__esphome__get_device_logs"
    ]
  },
  "mcpServers": {
    "esphome": {
      "command": "esphome-mcp",
      "env": {
        "ESPHOME_DASHBOARD_URL": "http://192.168.1.100:6052"
      }
    }
  }
}
```

### Docker

Build the image:

```bash
docker build -t esphome-mcp .
```

Run standalone:

```bash
docker run --rm \
  -e ESPHOME_DASHBOARD_URL=http://192.168.1.100:6052 \
  -p 8080:8080 \
  esphome-mcp
```

The Docker image runs the MCP server in HTTP mode on port 8080.

#### Docker Compose

```yaml
services:
  esphome:
    image: ghcr.io/esphome/esphome
    volumes:
      - ./esphome-config:/config
    ports:
      - "6052:6052"
    restart: unless-stopped

  esphome-mcp:
    image: ghcr.io/kdkavanagh/esphome-mcp:latest
    ports:
      - "8080:8080"
    environment:
      - ESPHOME_DASHBOARD_URL=http://esphome:6052
    # Uncomment if your dashboard has auth enabled:
    # - ESPHOME_DASHBOARD_USERNAME=admin
    # - ESPHOME_DASHBOARD_PASSWORD=your-password
    depends_on:
      - esphome
```

To use the Docker container with Claude Desktop, configure with the HTTP URL:

```json
{
  "mcpServers": {
    "esphome": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```



## Disclaimer

I had claude-code write this mcp server, under my (a professional software engineer with 15yrs of experience) supervision.  
