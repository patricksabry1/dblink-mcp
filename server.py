"""Backward-compatible module entrypoint."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from dblink_mcp.server import *  # noqa: F401,F403

if __name__ == "__main__":
    from dblink_mcp.server import main

    main()
