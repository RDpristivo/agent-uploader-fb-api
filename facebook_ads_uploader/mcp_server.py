import json
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List
import threading
import time
import inspect
import traceback

# Import MCP tool functions
from facebook_ads_uploader.mcp_tool import create_maximizer_campaign, ping

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp_server")


class MCPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Model Context Protocol (MCP)"""

    def _set_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self._set_headers()

    def do_GET(self):
        """Handle GET requests - used for health checks"""
        if self.path == "/health" or self.path == "/":
            self._set_headers()
            response = {"status": "ok", "message": "MCP server is running"}
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        """Handle POST requests for MCP endpoints"""
        if self.path == "/v1/messages":
            self._handle_messages()
        elif self.path == "/v1/tools":
            self._handle_tools()
        else:
            self.send_response(404)
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def _handle_messages(self):
        """Process /v1/messages API endpoint - wrapper for Claude API"""
        # Get request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._set_headers()
            response = {"error": "Empty request body"}
            self.wfile.write(json.dumps(response).encode())
            return

        request_body = self.rfile.read(content_length)
        try:
            request_data = json.loads(request_body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            response = {"error": "Invalid JSON"}
            self.wfile.write(json.dumps(response).encode())
            return

        # The actual handling of Claude API calls would go here
        # Instead, we'll return a notice that tool invocation should be used
        self._set_headers()
        response = {
            "id": "msg_01234567890123456789012345",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "This Model Context Protocol (MCP) server is configured for tool invocation only, not direct messaging. Please use the appropriate endpoints to interact with the Facebook Ads Uploader tool.",
                }
            ],
            "model": "facebook-ads-uploader-tool",
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        self.wfile.write(json.dumps(response).encode())

    def _handle_tools(self):
        """Process /v1/tools API endpoint for tool invocation"""
        # Get request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._set_headers()
            response = {"error": "Empty request body"}
            self.wfile.write(json.dumps(response).encode())
            return

        request_body = self.rfile.read(content_length)
        try:
            request_data = json.loads(request_body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            response = {"error": "Invalid JSON"}
            self.wfile.write(json.dumps(response).encode())
            return

        # Process tool invocation
        try:
            tool_name = request_data.get("name", "")
            parameters = request_data.get("parameters", {})

            # Map tool names to functions
            tool_functions = {
                "create_maximizer_campaign": create_maximizer_campaign,
                "ping": ping,
            }

            if tool_name not in tool_functions:
                self.send_response(400)
                self.end_headers()
                response = {"error": f"Unknown tool: {tool_name}"}
                self.wfile.write(json.dumps(response).encode())
                return

            # Get the function
            func = tool_functions[tool_name]

            # Extract expected parameters from function signature
            sig = inspect.signature(func)
            valid_params = {}

            # Filter parameters based on function signature
            for param_name, param in sig.parameters.items():
                if param_name in parameters:
                    valid_params[param_name] = parameters[param_name]
                elif (
                    param.default is inspect.Parameter.empty
                    and not param.kind == inspect.Parameter.VAR_KEYWORD
                ):
                    # Required parameter missing
                    self.send_response(400)
                    self.end_headers()
                    response = {"error": f"Missing required parameter: {param_name}"}
                    self.wfile.write(json.dumps(response).encode())
                    return

            # Execute the function
            logger.info(f"Executing tool: {tool_name}")
            result = func(**valid_params)

            # Return success response
            self._set_headers()
            response = {"status": "success", "result": result}
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Error processing tool request: {str(e)}")
            logger.error(traceback.format_exc())
            self.send_response(500)
            self.end_headers()
            response = {"error": f"Error: {str(e)}"}
            self.wfile.write(json.dumps(response).encode())


class MCPServer:
    """Model Context Protocol server implementation"""

    def __init__(self, port: int = 5000):
        """Initialize the MCP server

        Args:
            port: Port to run the server on
        """
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Start the MCP server in a background thread"""
        if self.thread and self.thread.is_alive():
            logger.warning("MCP server is already running")
            return

        def run_server():
            """Run the server in a thread"""
            try:
                server = HTTPServer(("0.0.0.0", self.port), MCPHandler)
                self.server = server
                logger.info(f"MCP server started on port {self.port}")
                server.serve_forever()
            except Exception as e:
                logger.error(f"Error starting MCP server: {str(e)}")

        self.thread = threading.Thread(target=run_server, daemon=True)
        self.thread.start()
        # Give server time to start
        time.sleep(0.5)
        return self.thread.is_alive()

    def stop(self):
        """Stop the MCP server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("MCP server stopped")
            self.server = None


# Example usage
if __name__ == "__main__":
    # Start server
    server = MCPServer(port=5000)
    if server.start():
        print("MCP Server running at http://0.0.0.0:5000/")
        print("Available tools:")
        print("  - create_maximizer_campaign: Create a Facebook ad campaign")
        print("  - ping: Check if the server is running")
        print("\nHealth check endpoint:")
        print("  - GET /health")
        print("\nPress Ctrl+C to stop the server")

        try:
            # Keep the main thread running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping server...")
            server.stop()
