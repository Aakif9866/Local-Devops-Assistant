"""Simulates the natural-language scenarios from the project spec by scripting the
same tool-chaining decisions a real MCP client's model would make. This does not
require a live LLM — it proves the tool plumbing supports these workflows; an actual
client just replaces this script's decision logic with a model's reasoning."""

import json
import subprocess
import sys


class MCPClient:
    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "server.py"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self._id = 0
        self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "initialize",
                     "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "scenario-test", "version": "1.0"}}})
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()

    def _next_id(self):
        self._id += 1
        return self._id

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())

    def call(self, tool, arguments=None):
        resp = self._send({"jsonrpc": "2.0", "id": self._next_id(), "method": "tools/call",
                            "params": {"name": tool, "arguments": arguments or {}}})
        result = resp["result"]
        structured = result.get("structuredContent")
        if structured is not None:
            return structured.get("result", structured)
        return json.loads(result["content"][0]["text"])

    def close(self):
        self.proc.terminate()


def scenario_1_is_postgres_running(client: MCPClient):
    print("\nScenario: 'Is PostgreSQL running properly?'")
    containers = client.call("list_containers")
    matches = [c for c in containers if "postgres" in c["name"].lower() and "Up" in c["status"]]
    assert matches, "expected at least one running postgres container"
    target = matches[0]["name"]
    print(f"  -> model would call list_containers, find '{target}' running")
    inspected = client.call("inspect_container", {"container_name": target})
    print(f"  -> model would call inspect_container('{target}')")
    healthy = inspected["health"] in ("healthy", "no healthcheck configured")
    answer = f"Yes, {target} is running (status: {inspected['status']}, health: {inspected['health']})."
    print(f"  Answer: {answer}")
    assert healthy, inspected


def scenario_2_is_port_accessible(client: MCPClient):
    print("\nScenario: 'Is port 15432 accessible?'")
    result = client.call("check_port", {"port": 15432})
    print("  -> model would call check_port(15432, 'localhost')")
    answer = f"{'Yes' if result['open'] else 'No'}, port 15432 is {'open' if result['open'] else 'closed'}."
    print(f"  Answer: {answer}")
    assert result["open"] is True, result


def scenario_3_unhealthy_containers(client: MCPClient):
    print("\nScenario: 'Which containers are unhealthy?'")
    containers = client.call("list_containers")
    running = [c for c in containers if "Up" in c["status"]]
    print(f"  -> model would call list_containers, then inspect_container for each of {len(running)} running containers")
    unhealthy = []
    for c in running:
        details = client.call("inspect_container", {"container_name": c["name"]})
        if details.get("health") not in ("healthy", "no healthcheck configured"):
            unhealthy.append((c["name"], details.get("health")))
    if unhealthy:
        answer = "Unhealthy: " + ", ".join(f"{n} ({h})" for n, h in unhealthy)
    else:
        answer = "All running containers are healthy or have no healthcheck configured."
    print(f"  Answer: {answer}")


def scenario_4_docker_down_diagnosis(client: MCPClient):
    print("\nScenario: 'Why is my container failing?' (asked about a container that doesn't exist)")
    result = client.call("inspect_container", {"container_name": "totally-made-up-name"})
    print("  -> model would call inspect_container('totally-made-up-name')")
    assert "error" in result, result
    answer = f"I couldn't find that container: {result['error']}. Try list_containers to see what's actually running."
    print(f"  Answer: {answer}")


def main():
    client = MCPClient()
    try:
        scenario_1_is_postgres_running(client)
        scenario_2_is_port_accessible(client)
        scenario_3_unhealthy_containers(client)
        scenario_4_docker_down_diagnosis(client)
        print("\nALL SCENARIO TESTS PASSED")
    finally:
        client.close()


if __name__ == "__main__":
    main()
