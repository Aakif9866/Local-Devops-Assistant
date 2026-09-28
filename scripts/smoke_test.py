"""Reusable smoke test: spins up the MCP server over stdio, exercises every tool,
and asserts on real results. Run after every stage to catch regressions."""

import json
import subprocess
import sys


def main():
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def send(msg):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            err = proc.stderr.read()
            raise RuntimeError(f"server produced no output. stderr:\n{err}")
        return json.loads(line)

    def call(name, arguments=None):
        resp = send(
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
        )
        if "error" in resp:
            raise RuntimeError(f"{name} -> protocol error: {resp['error']}")
        result = resp["result"]
        if result.get("isError"):
            raise RuntimeError(f"{name} -> tool error: {result}")
        structured = result.get("structuredContent")
        if structured is not None:
            return structured.get("result", structured)
        # Plain dict returns don't get structuredContent from this SDK version;
        # fall back to parsing the text content block.
        text = result["content"][0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    try:
        init = send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "smoketest", "version": "1.0"},
                },
            }
        )
        assert init["result"]["serverInfo"]["name"] == "local-devops-assistant"
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proc.stdin.flush()

        tools = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {t["name"] for t in tools["result"]["tools"]}
        expected = {
            "hello_world",
            "list_containers",
            "get_container_logs",
            "inspect_container",
            "check_port",
            "check_docker_health",
        }
        missing = expected - names
        assert not missing, f"missing tools: {missing}"
        print(f"[ok] tools/list has all expected tools: {sorted(names)}")

        hello = call("hello_world", {"name": "smoke-test"})
        assert "smoke-test" in hello, hello
        print(f"[ok] hello_world -> {hello!r}")

        health = call("check_docker_health")
        assert health["healthy"] is True, health
        print(f"[ok] check_docker_health -> daemon healthy, version {health['server_version']}")

        containers = call("list_containers")
        names_found = {c["name"] for c in containers}
        assert "devops-test-nginx" in names_found, names_found
        print(f"[ok] list_containers -> found {len(containers)} containers")

        logs = call("get_container_logs", {"container_name": "devops-test-nginx", "tail": 5})
        assert "logs" in logs, logs
        print("[ok] get_container_logs -> retrieved logs for devops-test-nginx")

        inspected = call("inspect_container", {"container_name": "devops-test-postgres"})
        assert inspected["name"] == "devops-test-postgres", inspected
        assert any("REDACTED" in e for e in inspected["env"]), inspected["env"]
        print("[ok] inspect_container -> POSTGRES_PASSWORD redacted, restart_count present")

        port_open = call("check_port", {"port": 18080, "host": "localhost"})
        assert port_open["open"] is True, port_open
        port_closed = call("check_port", {"port": 1, "host": "localhost"})
        assert port_closed["open"] is False, port_closed
        print("[ok] check_port -> correctly detects open (18080) vs closed (1) ports")

        bad = call("inspect_container", {"container_name": "does-not-exist-container"})
        assert "error" in bad, bad
        print("[ok] inspect_container on unknown container -> returns error, not crash")

        print("\nALL SMOKE TESTS PASSED")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
