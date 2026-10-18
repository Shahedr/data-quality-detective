"""The local startup command handles port conflicts without exposing the server."""
import socket

import pytest

from webapp.launch_local import LOCAL_HOST, available_port, main


def test_local_launcher_finds_an_unused_port_after_a_conflict():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as held:
        held.bind((LOCAL_HOST, 0))
        occupied = held.getsockname()[1]
        if occupied == 65535:
            pytest.skip("No higher port available for this test")
        result = available_port(occupied, min(occupied + 20, 65535))
        assert occupied < result <= min(occupied + 20, 65535)


def test_launcher_rejects_non_tcp_port_ranges():
    with pytest.raises(ValueError):
        available_port(0)
    with pytest.raises(ValueError):
        available_port(8500, 8400)
    with pytest.raises(ValueError):
        available_port(65536, 65537)


def test_startup_help_does_not_launch_browser_or_server():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
