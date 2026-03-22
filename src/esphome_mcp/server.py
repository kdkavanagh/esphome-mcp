from __future__ import annotations

from fastmcp import FastMCP

from esphome_mcp.client import client

mcp = FastMCP(
    name="ESPHome MCP",
    instructions=(
        "Interact with an ESPHome dashboard to list devices, "
        "check for updates, view configurations, and stream logs."
    ),
)


async def _resolve_device(device_name: str) -> dict | str:
    """Resolve a device name to its entry dict.

    Returns the device dict on success, or an error string if not found.
    """
    devices = await client.get_configured_devices()
    name_lower = device_name.lower()
    for device in devices:
        if (
            device.get("name", "").lower() == name_lower
            or device.get("friendly_name", "").lower() == name_lower
        ):
            return device

    available = [d.get("name", "unknown") for d in devices]
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
    try:
        devices = await client.get_configured_devices()
    except Exception as e:
        return f"Error fetching devices: {e}"

    if not devices:
        return "No devices found in the ESPHome dashboard."

    lines: list[str] = []
    for d in devices:
        name = d.get("friendly_name") or d.get("name", "unknown")
        config = d.get("configuration", "")
        deployed = d.get("deployed_version", "n/a")
        current = d.get("current_version", "n/a")
        address = d.get("address", "n/a")
        platform = d.get("target_platform", "n/a")

        lines.append(
            f"- {name}\n"
            f"  Config: {config}\n"
            f"  Deployed version: {deployed}\n"
            f"  Current version: {current}\n"
            f"  Address: {address}\n"
            f"  Platform: {platform}"
        )

    version = "unknown"
    try:
        version = await client.get_version()
    except Exception:
        pass

    header = f"ESPHome version: {version}\n{len(devices)} device(s):\n"
    return header + "\n".join(lines)


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
    try:
        result = await _resolve_device(device_name)
    except Exception as e:
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    name = device.get("friendly_name") or device.get("name", "unknown")
    deployed = device.get("deployed_version", "")
    current = device.get("current_version", "")

    if not deployed:
        return f"{name}: No deployed version found. The device may not have been flashed yet."

    if not current:
        return f"{name}: Running version {deployed}. Unable to determine if an update is available."

    if deployed != current:
        return f"{name}: Update available! Running {deployed}, latest is {current}."

    return f"{name}: Up to date at version {deployed}."


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
    try:
        result = await _resolve_device(device_name)
    except Exception as e:
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    filename = device.get("configuration", "")
    if not filename:
        return f"No configuration file found for device '{device_name}'."

    try:
        yaml_content = await client.get_configuration(filename)
    except Exception as e:
        return f"Error fetching configuration: {e}"

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

    try:
        result = await _resolve_device(device_name)
    except Exception as e:
        return f"Error: {e}"

    if isinstance(result, str):
        return result

    device = result
    filename = device.get("configuration", "")
    if not filename:
        return f"No configuration file found for device '{device_name}'."

    try:
        logs = await client.get_logs(filename, duration=float(duration))
    except Exception as e:
        return f"Error fetching logs: {e}"

    if not logs.strip():
        return f"No log output received from '{device_name}' within {duration} seconds. The device may be offline."

    return logs
