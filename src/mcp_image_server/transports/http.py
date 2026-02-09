"""
HTTP transport layer for MCP server.

This module implements the MCP Streamable HTTP transport protocol:
- POST /mcp/v1/messages - Send JSON-RPC messages
- GET  /mcp/v1/messages - Subscribe to SSE event stream
- DELETE /mcp/v1/sessions - Terminate session
"""

import asyncio
import json
import sys
from typing import Dict, Any, Optional, List
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, StreamingResponse
from starlette.datastructures import Headers
from sse_starlette import EventSourceResponse

from .session_manager import SessionManager, Session


class MCPHTTPHandler:
    """
    HTTP request handler for MCP protocol.

    Handles JSON-RPC message routing and SSE streaming for the MCP protocol.
    """

    # MCP Session header name
    SESSION_HEADER = "Mcp-Session-Id"

    def __init__(
        self,
        session_manager: SessionManager,
        enable_sse: bool = True,
        debug: bool = False
    ):
        """
        Initialize MCP HTTP handler.

        Args:
            session_manager: Session management instance
            enable_sse: Enable Server-Sent Events support
            debug: Enable debug logging
        """
        self.session_manager = session_manager
        self.enable_sse = enable_sse
        self.debug = debug

        # Store message handlers (will be set by server)
        self.json_rpc_handler: Optional[callable] = None

        # Event queues for SSE streams (session_id -> asyncio.Queue)
        self._sse_queues: Dict[str, asyncio.Queue] = {}

    def set_json_rpc_handler(self, handler: callable) -> None:
        """
        Set the JSON-RPC message handler.

        Args:
            handler: Async function that processes JSON-RPC messages
        """
        self.json_rpc_handler = handler

    def _debug_print(self, *args, **kwargs) -> None:
        """Print debug message to stderr."""
        if self.debug:
            print(*args, file=sys.stderr, **kwargs)

    def _extract_session_id(self, request: Request) -> Optional[str]:
        """
        Extract session ID from request headers.

        Args:
            request: HTTP request

        Returns:
            Optional[str]: Session ID if present
        """
        return request.headers.get(self.SESSION_HEADER)

    async def _create_or_get_session(self, session_id: Optional[str]) -> Session:
        """
        Create a new session or retrieve existing one.

        Args:
            session_id: Optional existing session ID

        Returns:
            Session: The session object
        """
        if session_id:
            session = await self.session_manager.get_session(session_id)
            if session:
                await self.session_manager.update_access_time(session_id)
                return session

        # Create new session
        return await self.session_manager.create_session()

    def _create_jsonrpc_error(
        self,
        code: int,
        message: str,
        request_id: Any = None,
        data: Optional[Any] = None
    ) -> Dict:
        """
        Create JSON-RPC error response.

        Args:
            code: Error code
            message: Error message
            request_id: Request ID
            data: Optional error data

        Returns:
            dict: JSON-RPC error response
        """
        error = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            },
            "id": request_id
        }

        if data is not None:
            error["error"]["data"] = data

        return error

    async def handle_post(self, request: Request) -> Response:
        """
        Handle POST /mcp/v1/messages - Receive JSON-RPC messages from client.

        Args:
            request: HTTP POST request

        Returns:
            Response: JSON response with result or error
        """
        # Extract session ID
        session_id = self._extract_session_id(request)
        self._debug_print(f"[POST] Session ID: {session_id}")

        # Get or create session
        session = await self._create_or_get_session(session_id)
        new_session = (session_id is None) or (session_id != session.session_id)

        try:
            # Parse JSON body
            try:
                body = await request.json()
            except json.JSONDecodeError as e:
                return JSONResponse(
                    self._create_jsonrpc_error(
                        -32700,
                        "Parse error: Invalid JSON",
                        data=str(e)
                    ),
                    status_code=400
                )

            self._debug_print(f"[POST] Request body: {json.dumps(body, indent=2)}")

            # Validate JSON-RPC structure
            if not isinstance(body, dict):
                return JSONResponse(
                    self._create_jsonrpc_error(
                        -32600,
                        "Invalid Request: Message must be a JSON object"
                    ),
                    status_code=400
                )

            if body.get("jsonrpc") != "2.0":
                return JSONResponse(
                    self._create_jsonrpc_error(
                        -32600,
                        "Invalid Request: Missing or invalid 'jsonrpc' field",
                        request_id=body.get("id")
                    ),
                    status_code=400
                )

            # Extract request fields
            method = body.get("method")
            request_id = body.get("id")

            if not method:
                return JSONResponse(
                    self._create_jsonrpc_error(
                        -32600,
                        "Invalid Request: Missing 'method' field",
                        request_id=request_id
                    ),
                    status_code=400
                )

            self._debug_print(f"[POST] Method: {method}, ID: {request_id}")

            # Check if handler is set
            if not self.json_rpc_handler:
                return JSONResponse(
                    self._create_jsonrpc_error(
                        -32603,
                        "Internal error: No JSON-RPC handler configured",
                        request_id=request_id
                    ),
                    status_code=500
                )

            # Call JSON-RPC handler
            try:
                result = await self.json_rpc_handler(body, session)
                self._debug_print(f"[POST] Handler result: {result}")
            except Exception as e:
                self._debug_print(f"[POST] Handler error: {e}")
                return JSONResponse(
                    self._create_jsonrpc_error(
                        -32603,
                        f"Internal error: {str(e)}",
                        request_id=request_id
                    ),
                    status_code=500
                )

            # Create response headers
            response_headers = {}
            if new_session:
                response_headers[self.SESSION_HEADER] = session.session_id
                self._debug_print(f"[POST] New session created: {session.session_id}")

            # Return success response
            return JSONResponse(
                result,
                headers=response_headers
            )

        except Exception as e:
            self._debug_print(f"[POST] Unexpected error: {e}")
            return JSONResponse(
                self._create_jsonrpc_error(
                    -32603,
                    f"Internal error: {str(e)}"
                ),
                status_code=500
            )

    async def handle_get(self, request: Request) -> Response:
        """
        Handle GET /mcp/v1/messages - Open SSE stream for server-to-client messages.

        Args:
            request: HTTP GET request

        Returns:
            Response: SSE event stream
        """
        if not self.enable_sse:
            return JSONResponse(
                {"error": "SSE is not enabled on this server"},
                status_code=501
            )

        # Extract session ID (required for GET)
        session_id = self._extract_session_id(request)
        if not session_id:
            return JSONResponse(
                {"error": "Mcp-Session-Id header is required for SSE stream"},
                status_code=400
            )

        # Validate session exists
        session = await self.session_manager.get_session(session_id)
        if not session:
            return JSONResponse(
                {"error": f"Session '{session_id}' not found or expired"},
                status_code=404
            )

        self._debug_print(f"[GET] Opening SSE stream for session: {session_id}")

        # Create event queue for this session if not exists
        if session_id not in self._sse_queues:
            self._sse_queues[session_id] = asyncio.Queue()

        # Event generator
        async def event_generator():
            """Generate SSE events from queue."""
            queue = self._sse_queues[session_id]
            event_id = 0

            try:
                # Send initial connection event
                yield {
                    "event": "connected",
                    "id": str(event_id),
                    "data": json.dumps({"status": "connected"})
                }
                event_id += 1

                # Stream events from queue
                while True:
                    try:
                        # Wait for event with timeout for keepalive
                        event_data = await asyncio.wait_for(
                            queue.get(),
                            timeout=30.0
                        )

                        yield {
                            "event": "message",
                            "id": str(event_id),
                            "data": json.dumps(event_data)
                        }
                        event_id += 1

                    except asyncio.TimeoutError:
                        # Send keepalive ping
                        yield {
                            "event": "ping",
                            "id": str(event_id),
                            "data": json.dumps({"type": "keepalive"})
                        }
                        event_id += 1

            except asyncio.CancelledError:
                self._debug_print(f"[GET] SSE stream cancelled for session: {session_id}")
                raise
            finally:
                # Cleanup on disconnect
                if session_id in self._sse_queues:
                    del self._sse_queues[session_id]
                self._debug_print(f"[GET] SSE stream closed for session: {session_id}")

        # Return SSE response
        return EventSourceResponse(
            event_generator(),
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    async def handle_delete(self, request: Request) -> Response:
        """
        Handle DELETE /mcp/v1/sessions - Terminate session.

        Args:
            request: HTTP DELETE request

        Returns:
            Response: 204 No Content on success
        """
        # Extract session ID
        session_id = self._extract_session_id(request)
        if not session_id:
            return JSONResponse(
                {"error": "Mcp-Session-Id header is required"},
                status_code=400
            )

        self._debug_print(f"[DELETE] Terminating session: {session_id}")

        # Delete session
        deleted = await self.session_manager.delete_session(session_id)

        if not deleted:
            return JSONResponse(
                {"error": f"Session '{session_id}' not found"},
                status_code=404
            )

        # Close SSE queue if exists
        if session_id in self._sse_queues:
            del self._sse_queues[session_id]

        # Return 204 No Content
        return Response(status_code=204)

    async def send_server_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Send a server-initiated message to client via SSE.

        Args:
            session_id: Target session ID
            message: JSON-RPC message to send

        Returns:
            bool: True if message was queued successfully
        """
        if not self.enable_sse:
            return False

        if session_id not in self._sse_queues:
            self._debug_print(f"[SSE] No SSE stream for session: {session_id}")
            return False

        queue = self._sse_queues[session_id]
        await queue.put(message)
        self._debug_print(f"[SSE] Message queued for session: {session_id}")
        return True


# Health check handler
async def health_check(request: Request) -> JSONResponse:
    """
    Health check endpoint.

    Returns:
        JSONResponse: Health status
    """
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-image-generation-http"
    })


# Export for convenience
__all__ = ["MCPHTTPHandler", "health_check"]
