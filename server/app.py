"""Root server entrypoint expected by OpenEnv tooling."""

from __future__ import annotations

import os

import uvicorn

from uniadmin.server.app import app


def main() -> None:
    """Run the UniAdmin ASGI app."""
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
