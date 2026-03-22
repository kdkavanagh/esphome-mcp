from __future__ import annotations

import asyncio
import base64
import json
import logging
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
        async with self._http_client() as client:
            resp = await client.get("/devices")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            configured: list[dict[str, Any]] = data.get("configured", [])
            importable: list[dict[str, Any]] = data.get("importable", [])
            return configured + importable

    async def get_configured_devices(self) -> list[dict[str, Any]]:
        """Fetch only configured devices from the dashboard."""
        async with self._http_client() as client:
            resp = await client.get("/devices")
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            result: list[dict[str, Any]] = data.get("configured", [])
            return result

    async def get_version(self) -> str:
        """Fetch the ESPHome version from the dashboard."""
        async with self._http_client() as client:
            resp = await client.get("/version")
            resp.raise_for_status()
            return resp.json().get("version", "unknown")

    async def get_configuration(self, filename: str) -> str:
        """Fetch the YAML configuration for a device."""
        if not filename.endswith((".yaml", ".yml")):
            raise ValueError(f"Invalid configuration filename: {filename}")
        async with self._http_client() as client:
            resp = await client.get("/edit", params={"configuration": filename})
            resp.raise_for_status()
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

        try:
            async with websockets.connect(
                ws_url,
                additional_headers=self._ws_auth_header,
            ) as ws:
                # Send the configuration to start log streaming
                await ws.send(json.dumps({"configuration": filename, "port": "OTA"}))

                try:
                    async with asyncio.timeout(duration):
                        async for raw_msg in ws:
                            msg = json.loads(raw_msg)
                            if msg.get("event") == "line":
                                lines.append(msg.get("data", ""))
                            elif msg.get("event") == "exit":
                                break
                except TimeoutError:
                    pass  # Expected — we collect for the requested duration
        except (websockets.exceptions.WebSocketException, OSError) as e:
            if lines:
                lines.append(f"\n[Connection closed: {e}]")
            else:
                raise

        return "\n".join(lines)


settings = ESPHomeSettings()  # type: ignore[call-arg]  # populated from env vars
client = ESPHomeClient(settings)
