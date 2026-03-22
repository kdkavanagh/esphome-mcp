import asyncio
import logging
import os

from esphome_mcp.client import get_client
from esphome_mcp.server import mcp

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(format=LOG_FORMAT, level=getattr(logging, level, logging.INFO))


def _check_connectivity() -> None:
    """Verify connectivity to the ESPHome dashboard by listing device names."""
    try:
        devices = asyncio.run(get_client().get_configured_devices())
        names = [d.get("name", "unknown") for d in devices]
        logger.info("Connected to ESPHome dashboard. Found %d device(s): %s", len(names), names)
    except Exception as e:
        logger.error("Failed to connect to ESPHome dashboard: %s", e)
        raise SystemExit(1) from e


def main() -> None:
    _configure_logging()
    _check_connectivity()
    mcp.run()


def main_web() -> None:
    _configure_logging()
    _check_connectivity()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
