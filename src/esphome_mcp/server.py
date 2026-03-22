from __future__ import annotations

import contextlib
import logging
from typing import Any

from fastmcp import FastMCP

from esphome_mcp.client import get_client

logger = logging.getLogger(__name__)

INSTRUCTIONS = """\
This server provides read-only access to an ESPHome dashboard.

## Workflow

1. **Always start by calling `list_device_names`** to get the list of known device names. \
Device names must match exactly (case-insensitive), so confirm the name against this list \
before passing it to any other tool.

2. Once you have a valid device name, use the other tools as needed:
   - `list_devices` — detailed info on all devices (versions, status, addresses, platform)
   - `check_device_update` — check if a firmware update is available
   - `get_device_status` — check if a device is online or offline
   - `get_device_configuration` — view the full YAML configuration
   - `get_device_logs` — stream recent logs (default 10s, max 30s). \
The device must be online for logs to be available.

## Important notes
- All tools are read-only. No changes can be made to devices or configurations.
- Device names are the ESPHome `name` field (e.g. "bike-outlet"), not the friendly name.
- If a tool returns "not found", re-check the name with `list_device_names`.
"""

mcp = FastMCP(
    name="ESPHome MCP",
    instructions=INSTRUCTIONS,
)


async def _resolve_device(device_name: str) -> dict[str, Any] | str:
    """Resolve a device name to its entry dict.

    Returns the device dict on success, or an error string if not found.
    """
    logger.debug("Resolving device name=%r", device_name)
    devices = await get_client().get_configured_devices()
    name_lower = device_name.lower()
    for device in devices:
        if (
            device.get("name", "").lower() == name_lower
            or device.get("friendly_name", "").lower() == name_lower
        ):
            logger.debug("Resolved %r to device config=%r", device_name, device.get("name"))
            return device

    available = [d.get("name", "unknown") for d in devices]
    logger.warning("Device %r not found. Available: %s", device_name, available)
    return f"Device '{device_name}' not found. Available devices: {', '.join(available)}"


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def list_devices() -> str:
    """List all devices configured in the ESPHome dashboard.

    Returns device names, versions, addresses, and online status.
    """
    logger.info("Listing all devices")
    try:
        devices = await get_client().get_configured_devices()
    except Exception as e:
        logger.error("Failed to fetch devices: %s", e)
        return f"Error fetching devices: {e}"

    if not devices:
        logger.info("No devices found")
        return "No devices found in the ESPHome dashboard."

    logger.info("Found %d device(s)", len(devices))

    lines: list[str] = []
    for d in devices:
        name = d.get("friendly_name") or d.get("name", "unknown")
        config = d.get("configuration", "")
        deployed = d.get("deployed_version", "n/a")
        current = d.get("current_version", "n/a")
        address = d.get("address", "n/a")
        platform = d.get("target_platform", "n/a")

        status = d.get("status", "unknown")

        lines.append(
            f"- {name}\n"
            f"  Config: {config}\n"
            f"  Status: {status}\n"
            f"  Deployed version: {deployed}\n"
            f"  Current version: {current}\n"
            f"  Address: {address}\n"
            f"  Platform: {platform}"
        )

    version = "unknown"
    with contextlib.suppress(Exception):
        version = await get_client().get_version()

    header = f"ESPHome version: {version}\n{len(devices)} device(s):\n"
    return header + "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def list_device_names() -> str:
    """List the names of all devices configured in the ESPHome dashboard.

    Returns only device names, one per line.
    """
    logger.info("Listing device names")
    try:
        devices = await get_client().get_configured_devices()
    except Exception as e:
        logger.error("Failed to fetch devices: %s", e)
        return f"Error fetching devices: {e}"

    if not devices:
        logger.info("No devices found")
        return "No devices found in the ESPHome dashboard."

    names = [d.get("name", "unknown") for d in devices]
    logger.info("Found %d device(s): %s", len(names), names)
    return "\n".join(names)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def check_device_update(device_name: str) -> str:
    """Check if a firmware update is available for an ESPHome device.

    Args:
        device_name: The name of the device (as shown in list_devices).
    """
    logger.info("Checking update for device=%r", device_name)
    try:
        result = await _resolve_device(device_name)
    except Exception as e:
        logger.error("Failed to resolve device %r: %s", device_name, e)
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    name = device.get("friendly_name") or device.get("name", "unknown")
    deployed = device.get("deployed_version", "")
    current = device.get("current_version", "")

    if not deployed:
        logger.info("Device %r has no deployed version", name)
        return f"{name}: No deployed version found. The device may not have been flashed yet."

    if not current:
        logger.info("Device %r: cannot determine available version", name)
        return f"{name}: Running version {deployed}. Unable to determine if an update is available."

    if deployed != current:
        logger.info("Device %r: update available %s -> %s", name, deployed, current)
        return f"{name}: Update available! Running {deployed}, latest is {current}."

    logger.info("Device %r: up to date at %s", name, deployed)
    return f"{name}: Up to date at version {deployed}."


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def get_device_status(device_name: str) -> str:
    """Check whether an ESPHome device is online or offline.

    Triggers a ping refresh and returns the current status.

    Args:
        device_name: The name of the device to check.
    """
    logger.info("Checking status for device=%r", device_name)
    try:
        with contextlib.suppress(Exception):
            await get_client().ping()
        result = await _resolve_device(device_name)
    except Exception as e:
        logger.error("Failed to get status for %r: %s", device_name, e)
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    name = device.get("friendly_name") or device.get("name", "unknown")
    status = device.get("status", "unknown")
    address = device.get("address", "n/a")

    logger.info("Device %r status=%s address=%s", name, status, address)
    return f"{name}: {status} (address: {address})"


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def get_device_configuration(device_name: str) -> str:
    """View the YAML configuration for an ESPHome device.

    Args:
        device_name: The name of the device whose configuration to view.
    """
    logger.info("Fetching configuration for device=%r", device_name)
    try:
        result = await _resolve_device(device_name)
    except Exception as e:
        logger.error("Failed to resolve device %r: %s", device_name, e)
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    filename = device.get("configuration", "")
    if not filename:
        logger.warning("Device %r has no configuration file", device_name)
        return f"No configuration file found for device '{device_name}'."

    try:
        logger.debug("Fetching config file=%r", filename)
        yaml_content = await get_client().get_configuration(filename)
    except Exception as e:
        logger.error("Failed to fetch configuration %r: %s", filename, e)
        return f"Error fetching configuration: {e}"

    logger.info("Returned configuration for %r (%d bytes)", device_name, len(yaml_content))
    return yaml_content


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
    }
)
async def get_device_logs(device_name: str, duration: int = 10) -> str:
    """View recent logs from an ESPHome device.

    Connects to the device and collects log output for the specified duration.

    Args:
        device_name: The name of the device to get logs from.
        duration: How many seconds to collect logs (default: 10, max: 30).
    """
    duration = max(1, min(30, duration))
    logger.info("Fetching logs for device=%r duration=%ds", device_name, duration)

    try:
        result = await _resolve_device(device_name)
    except Exception as e:
        logger.error("Failed to resolve device %r: %s", device_name, e)
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    filename = device.get("configuration", "")
    if not filename:
        logger.warning("Device %r has no configuration file", device_name)
        return f"No configuration file found for device '{device_name}'."

    try:
        logger.debug("Connecting to log stream for %r via %r", device_name, filename)
        logs = await get_client().get_logs(filename, duration=float(duration))
    except Exception as e:
        logger.error("Failed to fetch logs for %r: %s", device_name, e)
        return f"Error fetching logs: {e}"

    if not logs.strip():
        logger.info("No log output from %r within %ds", device_name, duration)
        return (
            f"No log output received from '{device_name}' within {duration} seconds. "
            f"The device may be offline."
        )

    logger.info("Collected %d bytes of logs from %r", len(logs), device_name)
    return logs
