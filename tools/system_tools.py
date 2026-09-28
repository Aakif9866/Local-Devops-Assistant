"""Generic system-level checks that aren't Docker-specific."""

import socket


def check_port_impl(port: int, host: str = "localhost") -> dict:
    """Check whether a TCP port is accessible on the given host."""
    if not (0 < port < 65536):
        return {"error": f"invalid port: {port}"}

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex((host, port))
        return {"host": host, "port": port, "open": result == 0}
    except socket.gaierror as exc:
        return {"host": host, "port": port, "open": False, "error": f"could not resolve host: {exc}"}
    finally:
        sock.close()
