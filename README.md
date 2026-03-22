# ESPHome MCP Server

An MCP (Model Context Protocol) server for interacting with an [ESPHome](https://esphome.io) dashboard. Provides read-only tools to list devices, check for updates, view configurations, and stream logs.

## Tools

| Tool | Description |
|------|-------------|
| `list_devices` | List all configured devices with versions, addresses, and platform info |
| `check_device_update` | Check if a firmware update is available for a specific device |
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

### Docker

Build the image:

```bash
docker build -t esphome-mcp .
```

Run standalone:

```bash
docker run -i --rm \
  -e ESPHOME_DASHBOARD_URL=http://192.168.1.100:6052 \
  esphome-mcp
```

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
    environment:
      - ESPHOME_DASHBOARD_URL=http://esphome:6052
    # Uncomment if your dashboard has auth enabled:
    # - ESPHOME_DASHBOARD_USERNAME=admin
    # - ESPHOME_DASHBOARD_PASSWORD=your-password
    stdin_open: true
    depends_on:
      - esphome
```

To use the Docker container with Claude Desktop, configure it with the `docker` command:

```json
{
  "mcpServers": {
    "esphome": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "ESPHOME_DASHBOARD_URL=http://192.168.1.100:6052",
        "ghcr.io/kdkavanagh/esphome-mcp:latest"
      ]
    }
  }
}
```
