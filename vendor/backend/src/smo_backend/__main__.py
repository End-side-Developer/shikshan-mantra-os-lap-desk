"""Entrypoint for ``python -m smo_backend``.

Starts Uvicorn bound to ``--host``/``--port`` (default ``0.0.0.0:8443`` per
ADR-0017). TLS is enabled only when BOTH ``--certfile`` and ``--keyfile`` are
provided; otherwise the server runs plain HTTP (local dev convenience). The
systemd unit always passes both cert paths — see systemd/smo-backend.service.
"""

from __future__ import annotations

import argparse

import uvicorn


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="smo_backend",
        description="Shikshan Mantra OS content backend (phase-1, /health only).",
    )
    p.add_argument("--host", default="0.0.0.0", help="bind address (default: 0.0.0.0)")
    p.add_argument("--port", type=int, default=8443, help="bind port (default: 8443, per ADR-0017)")
    p.add_argument(
        "--certfile",
        default=None,
        help="TLS certificate path; TLS is enabled only if --keyfile is also given",
    )
    p.add_argument(
        "--keyfile",
        default=None,
        help="TLS private-key path; TLS is enabled only if --certfile is also given",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    ssl_kwargs: dict[str, str] = {}
    if args.certfile and args.keyfile:
        ssl_kwargs = {"ssl_certfile": args.certfile, "ssl_keyfile": args.keyfile}
    uvicorn.run("smo_backend.app:app", host=args.host, port=args.port, **ssl_kwargs)


if __name__ == "__main__":
    main()
