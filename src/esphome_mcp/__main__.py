from esphome_mcp.server import mcp


def main() -> None:
    mcp.run()


def main_web() -> None:
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
