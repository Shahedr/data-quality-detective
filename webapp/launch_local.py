"""Open the local full-featured web app with a free loopback port.

Local-only: never binds to a public interface. Windows users can double-click
START_DATA_QUALITY_DETECTIVE.cmd instead of typing Uvicorn commands.
"""

import argparse
import socket
import threading
import time
import webbrowser

LOCAL_HOST = "127.0.0.1"


def available_port(preferred=8000, last=8099):
    """Pick a free local TCP port; binding remains limited to loopback."""
    if not (1 <= preferred <= last <= 65535):
        raise ValueError("Invalid loopback port range.")
    for port in range(preferred, last + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((LOCAL_HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError(
        f"No available local port between {preferred} and {last}. "
        "Close another running app or choose a different port."
    )


def launch(preferred=8000, open_browser=True):
    port = available_port(preferred)
    url = f"http://{LOCAL_HOST}:{port}"
    print(f"Data Quality Detective: starting local app at {url}", flush=True)
    print("Keep this window open. Press Ctrl+C to stop.", flush=True)
    import uvicorn
    config = uvicorn.Config(
        "webapp.app:app", host=LOCAL_HOST, port=port, log_level="info",
    )
    server = uvicorn.Server(config)
    if open_browser:
        def open_once_ready():
            # Wait for the server, not an arbitrary fixed delay.
            for _ in range(150):
                if server.started:
                    webbrowser.open(url)
                    return
                if server.should_exit:
                    return
                time.sleep(0.1)
        threading.Thread(target=open_once_ready, daemon=True).start()
    server.run()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Launch the local Data Quality Detective app in a browser."
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    return launch(args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
