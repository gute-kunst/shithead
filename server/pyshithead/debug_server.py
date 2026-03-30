from __future__ import annotations

import argparse
from urllib.parse import urlencode

import uvicorn

from pyshithead.debug_presets import DEBUG_PRESET_NAMES, DebugPresetSeed, seed_debug_preset
from pyshithead.main import create_app
from pyshithead.models.session import GameSessionManager


def create_debug_app(preset_name: str):
    session_manager = GameSessionManager()
    seed = seed_debug_preset(session_manager, preset_name)
    app = create_app(session_manager=session_manager, enable_debug_bootstrap=True)
    app.state.debug_preset_seed = seed
    return app, seed


def _browser_host(host: str) -> str:
    return "127.0.0.1" if host == "0.0.0.0" else host


def _debug_bootstrap_url(base_url: str, seed: DebugPresetSeed, token: str) -> str:
    query = urlencode({"invite": seed.session.invite_code, "token": token})
    return f"{base_url}/debug/session?{query}"


def _print_debug_banner(host: str, port: int, seed: DebugPresetSeed):
    base_url = f"http://{_browser_host(host)}:{port}"
    print("\n=== SHITHEAD DEBUG MODE ===")
    print(f"Preset: {seed.preset_name}")
    print(f"Invite code: {seed.session.invite_code}")
    for seat in seed.seats:
        role = "host" if seat.is_host else "player"
        print(
            f"Seat {seat.seat} ({seat.display_name}, {role}): "
            f"{_debug_bootstrap_url(base_url, seed, seat.token)}"
        )
    print("===========================\n")


def main():
    parser = argparse.ArgumentParser(description="Run the Shithead debug preset server.")
    parser.add_argument(
        "--preset",
        default="choose-public",
        choices=DEBUG_PRESET_NAMES,
        help="Debug preset to seed before startup.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the debug server to.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the debug server to.")
    args = parser.parse_args()

    app, seed = create_debug_app(args.preset)
    _print_debug_banner(args.host, args.port, seed)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
