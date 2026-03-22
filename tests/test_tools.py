from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastmcp.client import Client


@pytest.mark.asyncio
async def test_list_devices(mcp_client: Client) -> None:
    """list_devices should return both configured devices and ESPHome version."""
    result = await mcp_client.call_tool("list_devices", {})
    text = result.content[0].text

    assert "bike-outlet" in text.lower() or "Bike Outlet" in text
    assert "garage-sensor" in text.lower() or "Garage Sensor" in text
    assert "device(s)" in text


@pytest.mark.asyncio
async def test_list_device_names(mcp_client: Client) -> None:
    """list_device_names should return only device names, one per line."""
    result = await mcp_client.call_tool("list_device_names", {})
    text = result.content[0].text

    names = text.strip().split("\n")
    assert "bike-outlet" in names
    assert "garage-sensor" in names
    # Should not contain verbose details
    assert "Config:" not in text
    assert "Platform:" not in text


@pytest.mark.asyncio
async def test_list_devices_contains_platform(mcp_client: Client) -> None:
    """list_devices should include platform information."""
    result = await mcp_client.call_tool("list_devices", {})
    text = result.content[0].text

    # At least one device should show platform info
    assert "esp8266" in text.lower() or "esp32" in text.lower() or "Platform:" in text


@pytest.mark.asyncio
async def test_check_device_update_known_device(mcp_client: Client) -> None:
    """check_device_update should return a version status for a known device."""
    result = await mcp_client.call_tool("check_device_update", {"device_name": "bike-outlet"})
    text = result.content[0].text

    # Device hasn't been flashed, so expect "no deployed version" or similar
    assert "bike" in text.lower() or "Bike Outlet" in text
    assert "version" in text.lower()


@pytest.mark.asyncio
async def test_check_device_update_not_found(mcp_client: Client) -> None:
    """check_device_update should list available devices when name is wrong."""
    result = await mcp_client.call_tool(
        "check_device_update", {"device_name": "nonexistent-device"}
    )
    text = result.content[0].text

    assert "not found" in text.lower()
    assert "bike-outlet" in text


@pytest.mark.asyncio
async def test_get_device_configuration(mcp_client: Client) -> None:
    """get_device_configuration should return the YAML config content."""
    result = await mcp_client.call_tool("get_device_configuration", {"device_name": "bike-outlet"})
    text = result.content[0].text

    assert "name: bike-outlet" in text
    assert "esp8266" in text or "esp01_1m" in text
    assert "cse7766" in text


@pytest.mark.asyncio
async def test_get_device_configuration_second_device(mcp_client: Client) -> None:
    """get_device_configuration should work for the second device too."""
    result = await mcp_client.call_tool(
        "get_device_configuration", {"device_name": "garage-sensor"}
    )
    text = result.content[0].text

    assert "name: garage-sensor" in text
    assert "dht" in text


@pytest.mark.asyncio
async def test_get_device_configuration_not_found(mcp_client: Client) -> None:
    """get_device_configuration should return error for unknown device."""
    result = await mcp_client.call_tool("get_device_configuration", {"device_name": "nonexistent"})
    text = result.content[0].text

    assert "not found" in text.lower()


@pytest.mark.asyncio
async def test_get_device_logs_offline_device(mcp_client: Client) -> None:
    """get_device_logs should handle offline device gracefully."""
    result = await mcp_client.call_tool(
        "get_device_logs", {"device_name": "bike-outlet", "duration": 2}
    )
    text = result.content[0].text

    # Device is offline so we expect either an error message or "no output" message
    assert len(text) > 0


@pytest.mark.asyncio
async def test_get_device_status(mcp_client: Client) -> None:
    """get_device_status should return status for a known device."""
    result = await mcp_client.call_tool("get_device_status", {"device_name": "bike-outlet"})
    text = result.content[0].text

    assert "bike" in text.lower() or "Bike Outlet" in text
    assert "address" in text.lower()


@pytest.mark.asyncio
async def test_get_device_status_not_found(mcp_client: Client) -> None:
    """get_device_status should return error for unknown device."""
    result = await mcp_client.call_tool("get_device_status", {"device_name": "nonexistent"})
    text = result.content[0].text

    assert "not found" in text.lower()


@pytest.mark.asyncio
async def test_check_device_update_case_insensitive(mcp_client: Client) -> None:
    """Tools should resolve devices by name case-insensitively."""
    result = await mcp_client.call_tool("check_device_update", {"device_name": "Bike-Outlet"})
    text = result.content[0].text

    # Should resolve successfully via case-insensitive match on "name"
    assert "not found" not in text.lower()
    assert "version" in text.lower()


@pytest.mark.asyncio
async def test_get_device_version(mcp_client: Client) -> None:
    """get_device_version should return version info for a known device."""
    result = await mcp_client.call_tool("get_device_version", {"device_name": "bike-outlet"})
    text = result.content[0].text

    assert "bike" in text.lower() or "Bike Outlet" in text
    assert "version" in text.lower()


@pytest.mark.asyncio
async def test_get_device_version_not_found(mcp_client: Client) -> None:
    """get_device_version should return error for unknown device."""
    result = await mcp_client.call_tool("get_device_version", {"device_name": "nonexistent"})
    text = result.content[0].text

    assert "not found" in text.lower()


@pytest.mark.asyncio
async def test_get_esphome_schema_list_components(mcp_client: Client) -> None:
    """get_esphome_schema without component should list available components."""
    result = await mcp_client.call_tool("get_esphome_schema", {"version": "2025.8.0"})
    text = result.content[0].text

    assert "components" in text.lower()
    assert "sensor" in text
    assert "wifi" in text


@pytest.mark.asyncio
async def test_get_esphome_schema_specific_component(mcp_client: Client) -> None:
    """get_esphome_schema with component should return JSON schema."""
    result = await mcp_client.call_tool(
        "get_esphome_schema", {"version": "2025.8.0", "component": "sensor"}
    )
    text = result.content[0].text

    # Should be valid JSON schema content
    assert "sensor" in text.lower() or "{" in text


@pytest.mark.asyncio
async def test_get_esphome_schema_invalid_component(mcp_client: Client) -> None:
    """get_esphome_schema with invalid component should return error."""
    result = await mcp_client.call_tool(
        "get_esphome_schema", {"version": "2025.8.0", "component": "nonexistent_component"}
    )
    text = result.content[0].text

    assert "not found" in text.lower()
