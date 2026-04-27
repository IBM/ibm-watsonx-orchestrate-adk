import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlparse

import websockets
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles

from recording_server import RecordingServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "tmp"

app = FastAPI(title="Voice Runtime Browser Test", debug=True)
recording_server = RecordingServer(host="0.0.0.0", port=0, output_dir=str(OUTPUT_DIR))

# CDR Monitor - In-memory storage
cdr_reports: dict[str, dict] = {}
cdr_report_order: list[str] = []  # preserve insertion order

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    _logger.error(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors(), "body": str(exc.body)},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    _logger.error(f"HTTP exception on {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.on_event("startup")
async def startup_event():
    _logger.info("Application starting up")
    _logger.info(f"Output directory: {OUTPUT_DIR}")
    # Log all routes
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            _logger.info(f"Route: {route.path} - Methods: {route.methods}")

app.mount("/wavtools", StaticFiles(directory=BASE_DIR / "wavtools"), name="wavtools")


def _guess_media_type(path: Path) -> str:
    if path.suffix == ".js":
        return "application/javascript"
    if path.suffix == ".css":
        return "text/css"
    if path.suffix == ".html":
        return "text/html"
    return "application/octet-stream"


def _static_file_response(relative_path: str) -> FileResponse:
    file_path = (BASE_DIR / relative_path).resolve()
    if BASE_DIR.resolve() not in file_path.parents and file_path != BASE_DIR.resolve():
        raise HTTPException(status_code=404, detail="File not found")
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type=_guess_media_type(file_path))


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html", media_type="text/html")


@app.get("/index.html")
async def index_html() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html", media_type="text/html")


@app.get("/index.js")
async def index_js() -> FileResponse:
    return FileResponse(BASE_DIR / "index.js", media_type="application/javascript")


@app.get("/api/recordings")
async def list_recordings() -> JSONResponse:
    try:
        recordings = []
        if recording_server.output_dir.exists():
            for item in sorted(recording_server.output_dir.iterdir(), reverse=True):
                if item.is_dir():
                    metadata_file = item / "metadata.json"
                    metadata: dict[str, Any] = {}
                    if metadata_file.exists():
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)

                    recordings.append({
                        "id": item.name,
                        "path": str(item),
                        "name": item.name,
                        "metadata": metadata,
                    })

        return JSONResponse({
            "recordings": recordings,
            "count": len(recordings),
        })
    except Exception as e:
        _logger.error(f"Error listing recordings: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/recordings/{recording_id}")
async def get_recording_files(recording_id: str) -> JSONResponse:
    try:
        recording_dir = recording_server.output_dir / recording_id
        if not recording_dir.exists() or not recording_dir.is_dir():
            return JSONResponse({"error": "Recording not found"}, status_code=404)

        files = []
        for item in recording_dir.iterdir():
            if item.is_file():
                files.append({
                    "name": item.name,
                    "size": item.stat().st_size,
                    "type": item.suffix[1:] if item.suffix else "unknown",
                })

        return JSONResponse({
            "recording_id": recording_id,
            "files": files,
        })
    except Exception as e:
        _logger.error(f"Error getting recording files: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/recordings/{recording_id}/metadata")
async def get_metadata(recording_id: str) -> JSONResponse:
    try:
        metadata_file = recording_server.output_dir / recording_id / "metadata.json"
        if not metadata_file.exists():
            return JSONResponse({"error": "Metadata not found"}, status_code=404)

        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        return JSONResponse(metadata)
    except Exception as e:
        _logger.error(f"Error getting metadata: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# More specific route must come before the generic {role} route
@app.api_route("/api/recordings/{recording_id}/audio/interleaved", methods=["GET", "HEAD"])
async def get_interleaved_audio(recording_id: str, request: Request) -> Response:
    try:
        _logger.info(f"Interleaved audio request: method={request.method}, recording_id={recording_id}")
        audio_file = recording_server.output_dir / recording_id / "interleave.raw"
        _logger.info(f"Looking for file: {audio_file}")
        
        if not audio_file.exists():
            _logger.warning(f"Interleaved audio file not found: {audio_file}")
            return JSONResponse({"error": "Interleaved audio file not found"}, status_code=404)

        # Get file size for Content-Length header
        file_size = audio_file.stat().st_size
        _logger.info(f"File found, size: {file_size} bytes")
        
        headers = {
            "Content-Disposition": 'inline; filename="interleave.raw"',
            "Content-Length": str(file_size),
            "X-Sample-Rate": "16000",
            "X-Channels": "2",
            "X-Bit-Depth": "16",
            "X-Channel-Layout": "stereo (both channels mixed)",
        }

        # For HEAD requests, return headers only without body
        if request.method == "HEAD":
            _logger.info("Returning HEAD response with headers only")
            return Response(
                content=b"",
                media_type="application/octet-stream",
                headers=headers,
            )

        # For GET requests, return the full content
        _logger.info("Reading file content for GET request")
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        return Response(
            content=audio_data,
            media_type="application/octet-stream",
            headers=headers,
        )
    except Exception as e:
        _logger.error(f"Error getting interleaved audio: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.api_route("/api/recordings/{recording_id}/audio/{role}", methods=["GET", "HEAD"])
async def get_audio(recording_id: str, role: str, request: Request) -> Response:
    try:
        if role not in ["user", "agent"]:
            return JSONResponse({"error": "Invalid role. Must be 'user' or 'agent'"}, status_code=400)

        audio_file = recording_server.output_dir / recording_id / f"{role}.raw"
        if not audio_file.exists():
            return JSONResponse({"error": f"Audio file not found: {role}.raw"}, status_code=404)

        # Get file size for Content-Length header
        file_size = audio_file.stat().st_size
        
        headers = {
            "Content-Disposition": f'inline; filename="{role}.raw"',
            "Content-Length": str(file_size),
            "X-Sample-Rate": "16000",
            "X-Channels": "1",
            "X-Bit-Depth": "16",
        }

        # For HEAD requests, return headers only without body
        if request.method == "HEAD":
            return Response(
                content=b"",
                media_type="pcm_s16le",
                headers=headers,
            )

        # For GET requests, return the full content
        with open(audio_file, "rb") as f:
            audio_data = f.read()

        return Response(
            content=audio_data,
            media_type="pcm_s16le",
            headers=headers,
        )
    except Exception as e:
        _logger.error(f"Error getting audio: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/api/recordings/{recording_id}")
async def delete_recording(recording_id: str) -> JSONResponse:
    """Delete a call recording and all its associated files."""
    try:
        recording_dir = recording_server.output_dir / recording_id
        
        if not recording_dir.exists() or not recording_dir.is_dir():
            return JSONResponse({"error": "Recording not found"}, status_code=404)
        
        # Delete all files in the recording directory
        shutil.rmtree(recording_dir)
        
        _logger.info(f"Deleted recording: {recording_id}")
        
        return JSONResponse({
            "message": "Recording deleted successfully",
            "recording_id": recording_id
        })
    except Exception as e:
        _logger.error(f"Error deleting recording: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

# ============================================================================
# CDR Monitor API Endpoints
# ============================================================================

@app.post("/cdr-webhook")
async def receive_cdr_webhook(request: Request):
    """
    Webhook receiver for CDR (Call Detail Record) reports from voice runtime.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    report_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc).isoformat()

    cdr_reports[report_id] = {
        "id": report_id,
        "received_at": received_at,
        "payload": body,
    }
    cdr_report_order.append(report_id)

    _logger.info(f"Received CDR webhook: {report_id}")
    _logger.info(f"CDR payload keys: {list(body.keys()) if isinstance(body, dict) else 'not a dict'}")
    _logger.info(f"Total CDR reports stored: {len(cdr_reports)}")
    return JSONResponse({"status": "ok", "id": report_id}, status_code=201)


@app.get("/api/cdr/reports")
async def list_cdr_reports() -> JSONResponse:
    """
    List all CDR reports with summary information.
    """
    try:
        summary = []
        for rid in reversed(cdr_report_order):
            r = cdr_reports[rid]
            p = r["payload"]
            # Support both bare CDR and wrapped { "cdr": {...}, "message": "..." }
            cdr = p.get("cdr", p)
            call = cdr.get("call", {})
            turns = cdr.get("turns", [])
            summary.append({
                "id": rid,
                "received_at": r["received_at"],
                "transaction_id": cdr.get("transaction_id", "—"),
                "agent_id": cdr.get("agent_id", "—"),
                "environment_id": cdr.get("environment_id", "—"),
                "end_reason": call.get("end_reason", "—"),
                "start_timestamp": call.get("start_timestamp"),
                "milliseconds_elapsed": call.get("milliseconds_elapsed"),
                "turn_count": len(turns),
                "failure_occurred": cdr.get("failure_occurred", False),
                "system_error": cdr.get("system_error", False),
                "message": p.get("message", ""),
            })
        return JSONResponse(summary)
    except Exception as e:
        _logger.error(f"Error listing CDR reports: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/cdr/reports/{report_id}")
async def get_cdr_report(report_id: str) -> JSONResponse:
    """
    Get a specific CDR report by ID.
    """
    if report_id not in cdr_reports:
        raise HTTPException(status_code=404, detail="CDR report not found")
    return JSONResponse(cdr_reports[report_id])


@app.get("/api/cdr/reports/by-thread/{thread_id}")
async def get_cdr_report_by_thread_id(thread_id: str) -> JSONResponse:
    """
    Get CDR reports by thread_id.
    """
    def get_cdr(r):
        p = r["payload"]
        return p.get("cdr", p)
    
    matches = [
        r for r in cdr_reports.values()
        if get_cdr(r).get("thread_id") == thread_id
    ]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No CDR report found with thread_id '{thread_id}'")
    return JSONResponse(sorted(matches, key=lambda r: r["received_at"], reverse=True))


@app.get("/api/cdr/reports/by-transaction/{transaction_id}")
async def get_cdr_report_by_transaction_id(transaction_id: str) -> JSONResponse:
    """
    Get CDR reports by transaction_id.
    """
    def get_cdr(r):
        p = r["payload"]
        return p.get("cdr", p)
    
    matches = [
        r for r in cdr_reports.values()
        if get_cdr(r).get("transaction_id") == transaction_id
    ]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No CDR report found with transaction_id '{transaction_id}'")
    return JSONResponse(sorted(matches, key=lambda r: r["received_at"], reverse=True))


@app.delete("/api/cdr/reports")
async def clear_cdr_reports() -> JSONResponse:
    """
    Clear all CDR reports from memory.
    """
    cdr_reports.clear()
    cdr_report_order.clear()
    _logger.info("Cleared all CDR reports")
    return JSONResponse({"status": "cleared"})



@app.websocket("/record")
async def record(websocket: WebSocket):
    await websocket.accept()
    _logger.info("Recording websocket client connected")

    session = None

    try:
        while True:
            message = await websocket.receive()

            if "text" in message and message["text"] is not None:
                await recording_server._handle_control_message(websocket, message["text"], session)
                if session is None and recording_server.sessions:
                    session = list(recording_server.sessions.values())[-1]
            elif "bytes" in message and message["bytes"] is not None:
                if session:
                    await recording_server._handle_audio_frame(message["bytes"], session)
                else:
                    _logger.warning("Received audio frame before start message")
            elif message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        _logger.info("Recording websocket client disconnected")
    except Exception as e:
        _logger.error(f"Error handling recording websocket: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "status": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e),
                    "status_code": 500,
                },
            }))
        except Exception:
            pass
    finally:
        if session:
            _logger.info(f"Client disconnected, saving recording for transaction {session.transaction_id}")
            try:
                recording_path = session.save_recording(recording_server.output_dir)
                _logger.info(f"Recording saved to: {recording_path}")
            except Exception as e:
                _logger.error(f"Error saving recording: {e}", exc_info=True)

            if session.transaction_id in recording_server.sessions:
                del recording_server.sessions[session.transaction_id]


@app.websocket("/v1/conversation")
async def voice_runtime_proxy(websocket: WebSocket):
    """
    Proxy websocket endpoint that forwards connections from the browser
    to the actual voice runtime server specified in the connection settings.
    """
    await websocket.accept()
    _logger.info("Voice runtime proxy websocket client connected")
    
    # Extract query parameters
    query_params = dict(websocket.query_params)
    agent_id = query_params.get('agent_id')
    environment_id = query_params.get('environment_id')
    access_token = query_params.get('access_token')
    thread_id = query_params.get('thread_id')
    
    # Get the target voice runtime URL from query params or use default
    # The browser will send the URL they configured in settings
    target_url = query_params.get('target_url')
    
    if not target_url:
        _logger.error("No target_url provided in query parameters")
        await websocket.close(code=1008, reason="Missing target_url parameter")
        return
    
    # URL decode the target_url since it comes as a query parameter
    target_url = unquote(target_url).lstrip("\ufeff").strip()
    parsed_target_url = urlparse(target_url)
    if parsed_target_url.scheme not in {"ws", "wss"}:
        _logger.error(f"Invalid target_url websocket scheme: {target_url!r}")
        await websocket.close(code=1008, reason="target_url must start with ws:// or wss://")
        return
    
    _logger.info(f"Connecting to voice runtime at: {target_url}")
    _logger.info(f"Parameters: agent_id={agent_id}, environment_id={environment_id}, thread_id={thread_id}")
    
    # Build query string for the target server
    target_params = []
    if agent_id:
        target_params.append(f"agent_id={quote(agent_id, safe='')}")
    if environment_id:
        target_params.append(f"environment_id={quote(environment_id, safe='')}")
    if thread_id:
        target_params.append(f"thread_id={quote(thread_id, safe='')}")
    if access_token:
         target_params.append(f"access_token={quote(access_token, safe='')}")

    headers = {
        "Authorization": f"Bearer {quote(access_token, safe='')}"
    }

    separator = "&" if parsed_target_url.query else "?"
    target_url_with_params = f"{target_url}{separator}{'&'.join(target_params)}" if target_params else target_url
    
    _logger.info(f"Headers: {headers}")
    upstream_ws = None
    try:
        # Connect to the actual voice runtime server
        if parsed_target_url.scheme == "ws":
            upstream_ws = await websockets.connect(target_url_with_params, additional_headers=headers)
        else:
            upstream_ws = await websockets.connect(target_url_with_params, additional_headers=headers) 
            #upstream_ws = await websockets.connect(target_url_with_params, ssl=False, server_hostname=None, additional_headers=headers)
        _logger.info("Connected to upstream voice runtime server")
        
        # Create tasks to forward messages in both directions
        async def forward_to_upstream():
            """Forward messages from browser to voice runtime server"""
            try:
                while True:
                    message = await websocket.receive()
                    
                    if "text" in message and message["text"] is not None:
                        _logger.debug(f"Forwarding text message to upstream: {message['text'][:100]}")
                        await upstream_ws.send(message["text"])
                    elif "bytes" in message and message["bytes"] is not None:
                        _logger.debug(f"Forwarding binary message to upstream: {len(message['bytes'])} bytes")
                        await upstream_ws.send(message["bytes"])
                    elif message.get("type") == "websocket.disconnect":
                        _logger.info("Browser disconnected")
                        break
            except WebSocketDisconnect:
                _logger.info("Browser websocket disconnected")
            except Exception as e:
                _logger.error(f"Error forwarding to upstream: {e}", exc_info=True)
        
        async def forward_to_browser():
            """Forward messages from voice runtime server to browser"""
            try:
                async for message in upstream_ws:
                    if isinstance(message, str):
                        _logger.debug(f"Forwarding text message to browser: {message[:100]}")
                        await websocket.send_text(message)
                    elif isinstance(message, bytes):
                        _logger.debug(f"Forwarding binary message to browser: {len(message)} bytes")
                        await websocket.send_bytes(message)
            except Exception as e:
                _logger.error(f"Error forwarding to browser: {e}", exc_info=True)
        
        # Run both forwarding tasks concurrently
        await asyncio.gather(
            forward_to_upstream(),
            forward_to_browser(),
            return_exceptions=True
        )
        
    except websockets.exceptions.InvalidStatus as e:
        response = e.response
        response_headers = dict(response.headers) if response and response.headers else {}
        response_body = None
        if response and getattr(response, "body", None) is not None:
            try:
                response_body = response.body.decode("utf-8", errors="replace")
            except Exception:
                response_body = repr(response.body)
        _logger.error(
            "Upstream websocket handshake rejected: status=%s, reason=%s, headers=%s, body=%s",
            getattr(response, "status_code", None),
            getattr(response, "reason_phrase", None),
            response_headers,
            response_body,
            exc_info=True,
        )
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": {
                    "code": "UPSTREAM_CONNECTION_ERROR",
                    "message": f"Failed to connect to voice runtime server: {str(e)}",
                    "details": {
                        "status_code": getattr(response, "status_code", None),
                        "reason_phrase": getattr(response, "reason_phrase", None),
                        "headers": response_headers,
                        "body": response_body,
                    },
                }
            }))
        except Exception:
            pass
    except websockets.exceptions.WebSocketException as e:
        _logger.error(f"WebSocket error connecting to upstream: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": {
                    "code": "UPSTREAM_CONNECTION_ERROR",
                    "message": f"Failed to connect to voice runtime server: {str(e)}",
                }
            }))
        except Exception:
            pass
    except Exception as e:
        _logger.error(f"Error in voice runtime proxy: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "error": {
                    "code": "PROXY_ERROR",
                    "message": str(e),
                }
            }))
        except Exception:
            pass
    finally:
        if upstream_ws:
            await upstream_ws.close()
            _logger.info("Closed upstream websocket connection")


@app.get("/{file_path:path}")
async def static_files(file_path: str):
    if file_path.startswith("api/") or file_path == "record":
        raise HTTPException(status_code=404, detail="Not found")
    return _static_file_response(file_path)

# Made with Bob