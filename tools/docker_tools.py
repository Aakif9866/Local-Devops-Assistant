"""Docker inspection tools. All functions here are read-only: they never construct
a shell command from AI-provided free text, and they never call `docker exec`,
`docker run`, `docker rm`, etc."""

import json
import subprocess


def _run_docker(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a docker CLI command with a fixed argument list (never a shell string).

    Never raises: timeouts and a missing `docker` binary are converted into a
    CompletedProcess with a non-zero return code so every *_impl caller can keep
    using its existing `if result.returncode != 0` check instead of needing its
    own try/except for these cases.
    """
    try:
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=["docker", *args], returncode=-1,
            stdout="", stderr=f"docker command timed out after {timeout}s",
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=["docker", *args], returncode=-1,
            stdout="", stderr="docker CLI not found — is Docker installed and on PATH?",
        )


def list_containers_impl() -> list[dict]:
    """Return name, image, status, and ports for every container (running or stopped)."""
    result = _run_docker(["ps", "-a", "--format", "{{json .}}"])
    if result.returncode != 0:
        return [{"error": result.stderr.strip() or "docker ps failed"}]

    containers = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        containers.append(
            {
                "id": raw.get("ID"),
                "name": raw.get("Names"),
                "image": raw.get("Image"),
                "status": raw.get("Status"),
                "ports": raw.get("Ports"),
            }
        )
    return containers


def get_container_logs_impl(container_name: str, tail: int = 100) -> dict:
    """Return the last `tail` lines of a container's logs."""
    if not container_name or not container_name.strip():
        return {"error": "container_name must not be empty"}
    if tail <= 0:
        return {"error": f"tail must be a positive integer, got {tail}"}

    result = _run_docker(["logs", "--tail", str(tail), container_name])
    if result.returncode != 0:
        return {"error": result.stderr.strip() or f"could not get logs for {container_name}"}
    return {"container": container_name, "tail": tail, "logs": result.stdout.strip()}


_SENSITIVE_ENV_PATTERNS = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL", "PWD")


def _filter_env(env_list: list[str]) -> list[str]:
    """Mask values of environment variables whose name looks sensitive."""
    filtered = []
    for entry in env_list:
        key = entry.split("=", 1)[0]
        if any(pattern in key.upper() for pattern in _SENSITIVE_ENV_PATTERNS):
            filtered.append(f"{key}=***REDACTED***")
        else:
            filtered.append(entry)
    return filtered


def inspect_container_impl(container_name: str) -> dict:
    """Return config, health, network info, restart count, and exit code for a container."""
    if not container_name or not container_name.strip():
        return {"error": "container_name must not be empty"}

    result = _run_docker(["inspect", container_name])
    if result.returncode != 0:
        return {"error": result.stderr.strip() or f"container '{container_name}' not found"}

    try:
        data = json.loads(result.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return {"error": f"unexpected output from docker inspect for '{container_name}'"}

    state = data.get("State", {})
    config = data.get("Config", {})
    health = state.get("Health", {})

    return {
        "name": data.get("Name", "").lstrip("/"),
        "image": config.get("Image"),
        "env": _filter_env(config.get("Env", []) or []),
        "status": state.get("Status"),
        "health": health.get("Status", "no healthcheck configured"),
        "exit_code": state.get("ExitCode"),
        "restart_count": data.get("RestartCount"),
        "networks": list((data.get("NetworkSettings", {}).get("Networks", {}) or {}).keys()),
    }


def check_docker_health_impl() -> dict:
    """Check whether the Docker daemon is available and responding."""
    result = _run_docker(["info", "--format", "{{json .}}"], timeout=5)
    if result.returncode != 0:
        return {
            "healthy": False,
            "error": result.stderr.strip() or "Docker daemon is not responding",
        }
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"healthy": False, "error": "unexpected output from docker info"}
    return {
        "healthy": True,
        "server_version": info.get("ServerVersion"),
        "containers_running": info.get("ContainersRunning"),
        "containers_total": info.get("Containers"),
        "images": info.get("Images"),
    }
