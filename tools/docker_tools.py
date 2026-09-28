"""Docker inspection tools. All functions here are read-only: they never construct
a shell command from AI-provided free text, and they never call `docker exec`,
`docker run`, `docker rm`, etc."""

import json
import subprocess


def _run_docker(args: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a docker CLI command with a fixed argument list (never a shell string)."""
    return subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
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
        raw = json.loads(line)
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
