from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import zipfile
from typing import Any
from urllib.parse import urlparse

import httpx
import websockets
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class ESPHomeSettings(BaseSettings):
    """Configuration loaded from environment variables."""

    esphome_dashboard_url: str
    esphome_dashboard_username: str = ""
    esphome_dashboard_password: str = ""


class ESPHomeClient:
    """Async client for the ESPHome dashboard web API."""

    def __init__(self, settings: ESPHomeSettings) -> None:
        self._base_url = settings.esphome_dashboard_url.rstrip("/")
        self._auth: httpx.BasicAuth | None = None
        self._ws_auth_header: dict[str, str] = {}

        if settings.esphome_dashboard_username and settings.esphome_dashboard_password:
            self._auth = httpx.BasicAuth(
                settings.esphome_dashboard_username,
                settings.esphome_dashboard_password,
            )
            credentials = base64.b64encode(
                f"{settings.esphome_dashboard_username}:{settings.esphome_dashboard_password}".encode()
            ).decode()
            self._ws_auth_header = {"Authorization": f"Basic {credentials}"}
            logger.info("Configured Basic Auth for dashboard at %s", self._base_url)
        else:
            logger.info("Configured dashboard client at %s (no auth)", self._base_url)

    def _http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=30.0,
        )

    def _ws_url(self, path: str) -> str:
        parsed = urlparse(self._base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return f"{scheme}://{parsed.netloc}{parsed.path.rstrip('/')}/{path.lstrip('/')}"

    async def get_devices(self) -> list[dict[str, Any]]:
        """Fetch all devices from the dashboard."""
        logger.debug("GET /devices (all)")
        async with self._http_client() as client:
            resp = await client.get("/devices")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            configured: list[dict[str, Any]] = data.get("configured", [])
            importable: list[dict[str, Any]] = data.get("importable", [])
            logger.debug(
                "Got %d configured, %d importable devices", len(configured), len(importable)
            )
            return configured + importable

    async def get_configured_devices(self) -> list[dict[str, Any]]:
        """Fetch only configured devices from the dashboard."""
        logger.debug("GET /devices (configured only)")
        async with self._http_client() as client:
            resp = await client.get("/devices")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            result: list[dict[str, Any]] = data.get("configured", [])
            logger.debug("Got %d configured devices", len(result))
            return result

    async def get_version(self) -> str:
        """Fetch the ESPHome version from the dashboard."""
        logger.debug("GET /version")
        async with self._http_client() as client:
            resp = await client.get("/version")
            resp.raise_for_status()
            version: str = resp.json().get("version", "unknown")
            logger.debug("ESPHome version: %s", version)
            return version

    async def ping(self) -> None:
        """Request a ping status update for all devices."""
        logger.debug("GET /ping")
        async with self._http_client() as client:
            resp = await client.get("/ping")
            resp.raise_for_status()

    async def get_configuration(self, filename: str) -> str:
        """Fetch the YAML configuration for a device."""
        if not filename.endswith((".yaml", ".yml")):
            raise ValueError(f"Invalid configuration filename: {filename}")
        logger.debug("GET /edit?configuration=%s", filename)
        async with self._http_client() as client:
            resp = await client.get("/edit", params={"configuration": filename})
            resp.raise_for_status()
            logger.debug("Got configuration for %s (%d bytes)", filename, len(resp.text))
            return resp.text

    async def get_logs(self, filename: str, duration: float = 10.0) -> str:
        """Connect to the logs WebSocket and collect output for a duration.

        Args:
            filename: The device configuration filename.
            duration: Seconds to collect logs (default 10).

        Returns:
            Collected log lines joined by newlines.
        """
        ws_url = self._ws_url("/logs")
        lines: list[str] = []

        logger.debug(
            "Connecting to WebSocket %s for %s (duration=%.1fs)", ws_url, filename, duration
        )
        try:
            async with websockets.connect(
                ws_url,
                additional_headers=self._ws_auth_header,
            ) as ws:
                # Send the configuration to start log streaming
                await ws.send(
                    json.dumps({"type": "spawn", "configuration": filename, "port": "OTA"})
                )
                logger.debug("Sent log stream request for %s", filename)

                try:
                    async with asyncio.timeout(duration):
                        async for raw_msg in ws:
                            msg = json.loads(raw_msg)
                            if msg.get("event") == "line":
                                lines.append(msg.get("data", ""))
                            elif msg.get("event") == "exit":
                                exit_code = msg.get("code", "?")
                                logger.debug(
                                    "Log stream for %s exited with code %s", filename, exit_code
                                )
                                break
                except TimeoutError:
                    logger.debug(
                        "Log collection timed out after %.1fs (%d lines)", duration, len(lines)
                    )
        except (websockets.exceptions.WebSocketException, OSError) as e:
            if lines:
                logger.warning("WebSocket closed with %d lines collected: %s", len(lines), e)
                lines.append(f"\n[Connection closed: {e}]")
            else:
                logger.error("WebSocket connection failed for %s: %s", filename, e)
                raise

        logger.debug("Collected %d log lines from %s", len(lines), filename)
        return "\n".join(lines)


SCHEMA_URL_TEMPLATE = (
    "https://github.com/esphome/esphome-schema/releases/download/{version}/schema.zip"
)

# Cache: version -> {component_name: json_string}
_schema_cache: dict[str, dict[str, str]] = {}


async def fetch_schema(version: str, component: str | None = None) -> dict[str, str] | str:
    """Fetch and cache the ESPHome schema for a given version.

    Args:
        version: ESPHome version (e.g. "2026.3.0").
        component: Optional component name to return a single schema.

    Returns:
        If component is specified, returns the JSON string for that component.
        Otherwise returns a dict mapping component names to JSON strings.
    """
    if version not in _schema_cache:
        url = SCHEMA_URL_TEMPLATE.format(version=version)
        logger.info("Downloading ESPHome schema for version %s", version)
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        schemas: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    # Strip "schema/" prefix and ".json" suffix
                    component_name = name.rsplit("/", 1)[-1].removesuffix(".json")
                    schemas[component_name] = zf.read(name).decode()

        logger.info("Cached schema for version %s (%d components)", version, len(schemas))
        _schema_cache[version] = schemas

    cached = _schema_cache[version]
    if component is not None:
        if component not in cached:
            available = sorted(cached.keys())
            raise KeyError(
                f"Component '{component}' not found in schema {version}. "
                f"Available components ({len(available)}): {', '.join(available)}"
            )
        return cached[component]
    return cached


_client: ESPHomeClient | None = None
_settings_override: ESPHomeSettings | None = None


def configure(settings: ESPHomeSettings) -> None:
    """Set a custom settings override (e.g. for tests). Resets any existing client."""
    global _settings_override, _client
    _settings_override = settings
    _client = None
    logger.info("Client configured with override URL=%s", settings.esphome_dashboard_url)


def get_client() -> ESPHomeClient:
    """Return the shared client, creating it on first access."""
    global _client
    if _client is None:
        settings = _settings_override or ESPHomeSettings()  # type: ignore[call-arg]
        _client = ESPHomeClient(settings)
    return _client


def reset() -> None:
    """Clear the shared client (for test teardown)."""
    global _client, _settings_override
    _client = None
    _settings_override = None
    logger.info("Client reset")
