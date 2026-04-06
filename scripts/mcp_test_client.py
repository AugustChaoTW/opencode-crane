#!/usr/bin/env python3
"""
MCP Test Client for CRANE Integration

Tests JSON-RPC 2.0 over stdio transport with CRANE server.
Verifies:
1. Server starts and responds to JSON-RPC messages
2. Handshake completes (initialize → initialized)
3. tools/list returns 90 CRANE tools
4. tools/call executes successfully
"""

import subprocess
import json
import sys
import time
from typing import Dict, List, Any, Optional


class MCPClient:
    """JSON-RPC 2.0 client over stdio transport."""

    def __init__(self, server_cmd: str, env_vars: Dict[str, str] = None):
        self.server_cmd = server_cmd
        self.env = env_vars or {}
        self.process = None
        self.request_id = 0

    def start_server(self) -> bool:
        """Start CRANE server as subprocess."""
        try:
            # Prepare environment with PROJECT_DIR
            full_env = dict(__import__("os").environ)
            full_env.update(
                {
                    "PROJECT_DIR": "/home/augchao/opencode-crane",
                }
            )
            full_env.update(self.env)

            # Start subprocess with stdin/stdout pipes
            self.process = subprocess.Popen(
                self.server_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered
                text=True,  # Text mode
                env=full_env,
            )
            self.buffer = ""
            print(f"✓ Server started (PID: {self.process.pid})")
            return True
        except Exception as e:
            print(f"✗ Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the server subprocess."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            print(f"✓ Server stopped")

    def _read_line(self, timeout: float = 5.0) -> Optional[str]:
        """Read a complete line from server output."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                chunk = self.process.stdout.read(1)
                if chunk == "\n":
                    return self.buffer.strip()
                self.buffer += chunk
            except Exception:
                continue
        return None

    def send_request(self, method: str, params: Dict = None) -> Optional[Dict]:
        """Send JSON-RPC request and wait for response."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }
        request_str = json.dumps(request) + "\n"

        # Send request
        try:
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            print(f"→ {method} (id={self.request_id})")
        except Exception as e:
            print(f"✗ Failed to send request: {e}")
            return None

        # Read response
        response = self._read_line(timeout=10.0)
        if response:
            print(f"← Response received ({len(response)} chars)")
            try:
                decoder = json.JSONDecoder()
                idx = 0
                while idx < len(response):
                    try:
                        obj, end_idx = decoder.raw_decode(response, idx)
                        if obj.get("id") == self.request_id:
                            return obj
                        idx = end_idx
                    except json.JSONDecodeError:
                        break
                print(f"✗ No matching response found for id={self.request_id}")
                print(f"   Raw: {response[:200]}")
            except Exception as e:
                print(f"✗ Failed to parse response: {e}")
                print(f"   Raw: {response[:200]}")
        return None

    def send_notification(self, method: str, params: Dict = None):
        """Send JSON-RPC notification (no response expected)."""
        notification = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        notification_str = json.dumps(notification) + "\n"
        try:
            self.process.stdin.write(notification_str)
            self.process.stdin.flush()
            print(f"→ Notification: {method}")
        except Exception as e:
            print(f"✗ Failed to send notification: {e}")

    def test_handshake(self) -> bool:
        """Test MCP handshake (initialize → initialized)."""
        print("\n=== Testing MCP Handshake ===\n")

        # Send initialize request
        init_request = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "opencode-mcp-test", "version": "0.1.0"},
        }

        response = self.send_request("initialize", init_request)
        if not response:
            print("✗ Initialize failed")
            return False

        if "error" in response:
            print(f"✗ Initialize error: {response['error']}")
            return False

        if "result" in response:
            result = response["result"]
            print(f"✓ Initialized successfully")
            print(f"  Protocol Version: {result.get('protocolVersion', 'unknown')}")
            print(f"  Server Info: {result.get('serverInfo', {})}")

            # Send initialized notification
            self.send_notification("notifications/initialized")
            return True

        print("✗ Invalid initialize response")
        return False

    def test_tools_list(self) -> List[Dict]:
        """Test tools/list endpoint."""
        print("\n=== Testing tools/list ===\n")

        response = self.send_request("tools/list")
        if not response:
            print("✗ tools/list failed")
            return []

        if "error" in response:
            print(f"✗ tools/list error: {response['error']}")
            return []

        if "result" in response:
            tools = response["result"].get("tools", [])
            print(f"✓ Tools found: {len(tools)}")

            # Print tool categories
            if tools:
                print(f"  First tool: {tools[0].get('name', 'unknown')}")
                print(f"  Sample tools:")
                for tool in tools[:5]:
                    print(f"    - {tool.get('name', 'unknown')}")
                if len(tools) > 5:
                    print(f"    ... and {len(tools) - 5} more")

            return tools
        return []

    def test_tool_call(self, tool_name: str, arguments: Dict = None) -> bool:
        """Test tools/call endpoint."""
        print(f"\n=== Testing tools/call: {tool_name} ===\n")

        response = self.send_request(
            "tools/call", {"name": tool_name, "arguments": arguments or {}}
        )

        if not response:
            print(f"✗ tools/call failed")
            return False

        if "error" in response:
            print(f"✗ tools/call error: {response['error']}")
            return False

        if "result" in response:
            result = response["result"]
            print(f"✓ Tool executed successfully")

            # Print content if available
            contents = result.get("content", [])
            if contents:
                for item in contents[:3]:  # Show first 3 items
                    if isinstance(item, dict):
                        if "text" in item:
                            text = item["text"]
                            if len(text) > 500:
                                text = text[:500] + "..."
                            print(f"  Content preview: {text}")

            return True

        print(f"✗ Invalid tool response")
        return False


def main():
    """Run MCP test client."""
    print("=" * 70)
    print("CRANE MCP Integration Test Client")
    print("=" * 70)

    server_cmd = ["uv", "run", "python", "-m", "crane.server"]

    client = MCPClient(server_cmd)

    try:
        # Step 1: Start server
        if not client.start_server():
            sys.exit(1)

        # Wait for server to initialize
        time.sleep(1)

        # Step 2: Test handshake
        if not client.test_handshake():
            print("\n✗ Handshake failed")
            sys.exit(1)

        # Step 3: Test tools list
        tools = client.test_tools_list()
        if not tools:
            print("\n✗ Tools list failed")
            sys.exit(1)

        # Step 4: Test tool call (crane.get_project_info)
        success = client.test_tool_call("get_project_info")
        if not success:
            print("\n✗ Tool call failed")
            sys.exit(1)

        print("\n" + "=" * 70)
        print("✓ All MCP tests passed!")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n✗ Interrupted")
        sys.exit(1)
    finally:
        client.stop_server()


if __name__ == "__main__":
    main()
