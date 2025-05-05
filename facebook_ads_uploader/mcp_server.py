import json
import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
import threading
import anthropic
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("mcp_server")


class MCPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the Model Context Protocol (MCP)"""

    def __init__(self, *args, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=self.api_key) if api_key else None
        super().__init__(*args, **kwargs)

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

    def do_POST(self):
        """Handle POST requests for Claude messaging"""
        if self.path == "/v1/messages":
            self._handle_messages()
        else:
            self.send_response(404)
            self.end_headers()
            response = {"error": "Not found"}
            self.wfile.write(json.dumps(response).encode())

    def _handle_messages(self):
        """Process /v1/messages API endpoint"""
        # Verify API key exists
        if not self.client:
            self.send_response(401)
            self.end_headers()
            response = {"error": "API key not configured"}
            self.wfile.write(json.dumps(response).encode())
            return

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

        # Process the Claude message request
        try:
            # Extract input from the request
            model = request_data.get("model", "claude-3-opus-20240229")
            max_tokens = request_data.get("max_tokens", 1024)
            messages = request_data.get("messages", [])
            system = request_data.get("system", "")

            # Call Claude API
            response = self.client.messages.create(
                model=model, max_tokens=max_tokens, messages=messages, system=system
            )

            # Return Claude response
            self._set_headers()
            self.wfile.write(json.dumps(response.dict()).encode())

        except Exception as e:
            logger.error(f"Error processing Claude request: {str(e)}")
            self.send_response(500)
            self.end_headers()
            response = {"error": f"Error: {str(e)}"}
            self.wfile.write(json.dumps(response).encode())


class MCPServer:
    """Model Context Protocol server implementation"""

    def __init__(self, port: int = 5000, api_key: Optional[str] = None):
        """Initialize the MCP server

        Args:
            port: Port to run the server on
            api_key: Anthropic API key (if not provided, will try to load from env)
        """
        self.port = port
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.server = None
        self.thread = None

        if not self.api_key:
            logger.warning(
                "No Anthropic API key provided. Claude functionality will be disabled."
            )

    def handler_factory(self, *args, **kwargs):
        """Factory function to create handler instances with API key"""
        return MCPHandler(*args, api_key=self.api_key, **kwargs)

    def start(self):
        """Start the MCP server in a background thread"""
        if self.thread and self.thread.is_alive():
            logger.warning("MCP server is already running")
            return

        def run_server():
            """Run the server in a thread"""
            try:
                server = HTTPServer(
                    ("localhost", self.port),
                    lambda *args, **kwargs: self.handler_factory(*args, **kwargs),
                )
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
    # Load API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print(
            "Warning: No Anthropic API key found. Set the ANTHROPIC_API_KEY environment variable."
        )

    # Start server
    server = MCPServer(port=5000, api_key=api_key)
    if server.start():
        print("MCP Server running at http://localhost:5000/")
        print("Press Ctrl+C to stop the server")

        try:
            # Keep the main thread running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping server...")
            server.stop()
