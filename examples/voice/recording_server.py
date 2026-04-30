"""
WebSocket-based call recording server for browser_test.

This module implements a simple recording server that accepts WebSocket connections,
receives audio frames with custom binary framing, and saves recordings to disk.
"""

import asyncio
import logging
import json
import struct
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    import websockets
    from websockets.exceptions import WebSocketException
except ImportError:
    websockets = None
    WebSocketException = Exception

try:
    from aiohttp import web
except ImportError:
    web = None

_logger = logging.getLogger(__name__)


class RoleId:
    """Role identifiers for audio streams."""
    USER = 0x01
    AGENT = 0x02


class RecordingSession:
    """Manages a single recording session."""
    
    def __init__(self, transaction_id: str, thread_id: Optional[str] = None):
        self.transaction_id = transaction_id
        self.thread_id = thread_id
        self.start_time = datetime.utcnow()
        self.user_frames = 0
        self.agent_frames = 0
        self.user_audio = bytearray()
        self.agent_audio = bytearray()
        self.recording_file: Optional[Path] = None
        # Store frames with timestamps for interleaving
        self.user_frames_with_ts = []  # List of (timestamp_ms, audio_data)
        self.agent_frames_with_ts = []  # List of (timestamp_ms, audio_data)
    
    def add_audio_frame(self, role_id: int, audio_data: bytes, timestamp_ms: int):
        """Add audio frame to the appropriate stream with timestamp."""
        if role_id == RoleId.USER:
            self.user_audio.extend(audio_data)
            self.user_frames += 1
            self.user_frames_with_ts.append((timestamp_ms, audio_data))
        elif role_id == RoleId.AGENT:
            self.agent_audio.extend(audio_data)
            self.agent_frames += 1
            self.agent_frames_with_ts.append((timestamp_ms, audio_data))
    
    def create_interleaved_audio(self) -> bytes:
        """
        Create stereo audio with both user and agent mixed into both channels.
        Uses sequential frame ordering to avoid overlaps and corruption.
        Both voices are heard in both ears.
        
        Returns:
            Stereo interleaved audio data as bytes (16-bit PCM, 2 channels)
        """
        if not self.user_frames_with_ts and not self.agent_frames_with_ts:
            return b''
        
        import struct
        
        # Sort all frames by timestamp to process them in order
        all_frames = []
        for timestamp_ms, audio_data in self.user_frames_with_ts:
            all_frames.append((timestamp_ms, 'user', audio_data))
        for timestamp_ms, audio_data in self.agent_frames_with_ts:
            all_frames.append((timestamp_ms, 'agent', audio_data))
        
        all_frames.sort(key=lambda x: x[0])
        
        if not all_frames:
            return b''
        
        # Track the last written position for each role to handle sequential appending
        user_last_pos = 0
        agent_last_pos = 0
        
        # Calculate approximate total duration
        start_time = all_frames[0][0]
        end_time = all_frames[-1][0]
        duration_ms = end_time - start_time + 100  # Add buffer
        total_samples = int((duration_ms / 1000.0) * 16000)
        
        # Create separate buffers for user and agent
        user_buffer = [0] * total_samples
        agent_buffer = [0] * total_samples
        
        # Process frames in timestamp order
        for timestamp_ms, role, audio_data in all_frames:
            # Calculate target position based on timestamp
            offset_ms = timestamp_ms - start_time
            target_pos = int((offset_ms / 1000.0) * 16000)
            
            # Convert audio data to samples
            num_samples = len(audio_data) // 2
            samples = []
            for i in range(num_samples):
                sample_value = struct.unpack('<h', audio_data[i*2:(i+1)*2])[0]
                samples.append(sample_value)
            
            if role == 'user':
                # Use the later of target_pos or last written position
                write_pos = max(target_pos, user_last_pos)
                for i, sample in enumerate(samples):
                    if write_pos + i < len(user_buffer):
                        user_buffer[write_pos + i] = sample
                user_last_pos = write_pos + len(samples)
            else:  # agent
                # Use the later of target_pos or last written position
                write_pos = max(target_pos, agent_last_pos)
                for i, sample in enumerate(samples):
                    if write_pos + i < len(agent_buffer):
                        agent_buffer[write_pos + i] = sample
                agent_last_pos = write_pos + len(samples)
        
        # Mix the two buffers together
        # Use the minimum of (max last position, buffer size) to avoid index errors
        max_len = min(max(user_last_pos, agent_last_pos), len(user_buffer), len(agent_buffer))
        mixed_buffer = []
        for i in range(max_len):
            mixed_sample = user_buffer[i] + agent_buffer[i]
            # Clip to int16 range
            mixed_sample = max(-32768, min(32767, mixed_sample))
            mixed_buffer.append(mixed_sample)
        
        # Create stereo audio by duplicating the mixed buffer to both channels
        stereo_audio = bytearray()
        for sample in mixed_buffer:
            sample_bytes = struct.pack('<h', sample)
            stereo_audio.extend(sample_bytes)  # Left channel
            stereo_audio.extend(sample_bytes)  # Right channel
        
        return bytes(stereo_audio)
    
    def get_duration_ms(self) -> int:
        """Calculate recording duration in milliseconds."""
        return int((datetime.utcnow() - self.start_time).total_seconds() * 1000)
    
    def save_recording(self, output_dir: Path) -> Path:
        """
        Save recording to disk as separate user and agent files, plus interleaved audio.
        
        Returns:
            Path to the saved recording directory
        """
        # Create timestamp-based filename
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        recording_dir = output_dir / f"{timestamp}-call-recording"
        recording_dir.mkdir(parents=True, exist_ok=True)
        
        _logger.info(f"Here's the user audio: {len(self.user_audio)}")
        # Save user audio
        if self.user_audio:
            user_file = recording_dir / "user.raw"
            with open(user_file, "wb") as f:
                f.write(self.user_audio)
            _logger.info(f"Saved user audio: {user_file} ({len(self.user_audio)} bytes)")
        
        # Save agent audio
        _logger.info(f"Here's the agent audio: {len(self.agent_audio)}")
        if self.agent_audio:
            agent_file = recording_dir / "agent.raw"
            with open(agent_file, "wb") as f:
                f.write(self.agent_audio)
            _logger.info(f"Saved agent audio: {agent_file} ({len(self.agent_audio)} bytes)")
        
        # Create and save interleaved audio (stereo: both channels contain mixed user+agent audio)
        interleaved_audio = self.create_interleaved_audio()
        if interleaved_audio:
            interleaved_file = recording_dir / "interleave.raw"
            with open(interleaved_file, "wb") as f:
                f.write(interleaved_audio)
            _logger.info(f"Saved stereo interleaved audio: {interleaved_file} ({len(interleaved_audio)} bytes, both channels mixed)")
        
        # Save metadata
        metadata = {
            "transaction_id": self.transaction_id,
            "thread_id": self.thread_id,
            "start_time": self.start_time.isoformat() + "Z",
            "duration_ms": self.get_duration_ms(),
            "user_frames": self.user_frames,
            "agent_frames": self.agent_frames,
            "user_bytes": len(self.user_audio),
            "agent_bytes": len(self.agent_audio),
            "interleaved_bytes": len(interleaved_audio) if interleaved_audio else 0,
        }
        
        metadata_file = recording_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        _logger.info(f"Saved metadata: {metadata_file}")
        
        self.recording_file = recording_dir
        return recording_dir


class RecordingServer:
    """WebSocket server for call recording."""
    
    def __init__(self, host: str = "localhost", port: int = 9825, output_dir: Optional[str] = None):
        """
        Initialize recording server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            output_dir: Directory to save recordings (defaults to ./tmp relative to this file)
        """
        if websockets is None:
            raise ImportError(
                "websockets library is required for RecordingServer. "
                "Install with: pip install websockets"
            )
        
        self.host = host
        self.port = port
        # Default to ./tmp directory relative to this file's location
        if output_dir is None:
            script_dir = Path(__file__).parent
            self.output_dir = script_dir / "tmp"
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, RecordingSession] = {}
    
    async def handle_client(self, websocket):
        """Handle a client connection."""
        _logger.info(f"Client connected from {websocket.remote_address}")
        _logger.info(f"Client headers: {websocket.request.headers}")

        session: Optional[RecordingSession] = None
        
        try:
            async for message in websocket:
                # Check if message is text (JSON control message) or binary (audio frame)
                if isinstance(message, str):
                    await self._handle_control_message(websocket, message, session)
                    # Update session reference after handling start message
                    if session is None and self.sessions:
                        # Get the most recently created session
                        session = list(self.sessions.values())[-1]
                elif isinstance(message, bytes):
                    if session:
                        await self._handle_audio_frame(message, session)
                    else:
                        _logger.warning("Received audio frame before start message")
        
        except WebSocketException as e:
            _logger.error(f"WebSocket error: {e}")
        except Exception as e:
            _logger.error(f"Error handling client: {e}", exc_info=True)
        finally:
            # Clean up session on disconnect
            if session:
                _logger.info(f"Client disconnected, saving recording for transaction {session.transaction_id}")
                try:
                    recording_path = session.save_recording(self.output_dir)
                    _logger.info(f"Recording saved to: {recording_path}")
                except Exception as e:
                    _logger.error(f"Error saving recording: {e}", exc_info=True)
                
                # Remove from active sessions
                if session.transaction_id in self.sessions:
                    del self.sessions[session.transaction_id]
    
    async def _handle_control_message(
        self,
        websocket,
        message: str,
        session: Optional[RecordingSession]
    ):
        """Handle JSON control messages."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "start":
                await self._handle_start_message(websocket, data)
            elif message_type == "stop":
                await self._handle_stop_message(websocket, data, session)
            else:
                _logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError as e:
            _logger.error(f"Invalid JSON message: {e}")
        except Exception as e:
            _logger.error(f"Error handling control message: {e}", exc_info=True)
    
    async def _handle_start_message(self, websocket, data: Dict[str, Any]):
        """Handle start recording message."""
        event_id = data.get("event_id")
        session_data = data.get("session", {})
        transaction_id = session_data.get("transaction_id")
        thread_id = session_data.get("thread_id")
        
        _logger.info(f"Start recording request: event_id={event_id}, transaction_id={transaction_id}")
        
        # Create new recording session
        session = RecordingSession(transaction_id=transaction_id, thread_id=thread_id)
        self.sessions[transaction_id] = session
        
        # Send started response
        response = {
            "type": "started",
            "event_id": event_id,
            "transaction_id": transaction_id,
            "thread_id": thread_id,
            "status": "ready"
        }
        
        await websocket.send_json(response)
        _logger.info(f"Recording started for transaction {transaction_id}")
    
    async def _handle_stop_message(
        self,
        websocket,
        data: Dict[str, Any],
        session: Optional[RecordingSession]
    ):
        """Handle stop recording message."""
        event_id = data.get("event_id")
        transaction_id = data.get("transaction_id")
        thread_id = data.get("thread_id")
        
        _logger.info(f"Stop recording request: event_id={event_id}, transaction_id={transaction_id}")
        
        if session:
            # Save recording
            try:
                recording_path = session.save_recording(self.output_dir)
                duration_ms = session.get_duration_ms()
                
                # Send stopped response
                response = {
                    "type": "stopped",
                    "event_id": event_id,
                    "transaction_id": transaction_id,
                    "thread_id": thread_id,
                    "metadata": {
                        "duration_milliseconds": duration_ms,
                        "user_frames": session.user_frames,
                        "agent_frames": session.agent_frames,
                        "recording_path": str(recording_path)
                    }
                }
                
                await websocket.send_json(response)
                _logger.info(f"Recording stopped for transaction {transaction_id}, duration: {duration_ms}ms")
                
                # Remove from active sessions
                if transaction_id in self.sessions:
                    del self.sessions[transaction_id]
            
            except Exception as e:
                _logger.error(f"Error stopping recording: {e}", exc_info=True)
                # Send error response
                error_response = {
                    "type": "error",
                    "event_id": event_id,
                    "status": "error",
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(e),
                        "status_code": 500
                    }
                }
                await websocket.send_json(error_response)
        else:
            _logger.warning(f"No active session for transaction {transaction_id}")
    
    async def _handle_audio_frame(self, data: bytes, session: RecordingSession):
        """Handle binary audio frame."""
        try:
            # Parse frame header (11 bytes) - matches audio_frame.py format
            # Format: role_id (1), seq (4), timestamp_ms (4), payload_length (2)
            if len(data) < 11:
                _logger.warning(f"Audio frame too short: {len(data)} bytes")
                return
            
            # Unpack header: role_id (1), seq (4), timestamp (4), length (2)
            role_id = data[0]
            seq = struct.unpack(">I", data[1:5])[0]
            timestamp_ms = struct.unpack(">I", data[5:9])[0]
            payload_length = struct.unpack(">H", data[9:11])[0]
            
            # Extract audio data
            audio_data = data[11:11 + payload_length]
            
            if len(audio_data) != payload_length:
                _logger.warning(
                    f"Audio data length mismatch: got {len(audio_data)}, expected {payload_length}"
                )
                return
            
            # Add to session with timestamp
            session.add_audio_frame(role_id, audio_data, timestamp_ms)
            
            role_name = "USER" if role_id == RoleId.USER else "AGENT"
            _logger.debug(
                f"Received audio frame: role={role_name}, seq={seq}, "
                f"timestamp={timestamp_ms}, length={payload_length}"
            )
        
        except Exception as e:
            _logger.error(f"Error parsing audio frame: {e}", exc_info=True)
    
    async def start(self):
        """Start the recording server."""
        _logger.info(f"Starting recording server on {self.host}:{self.port}")
        _logger.info(f"Recordings will be saved to: {self.output_dir}")
        
        async with websockets.serve(self.handle_client, self.host, self.port):
            _logger.info(f"Recording server listening on ws://{self.host}:{self.port}/record")
            await asyncio.Future()  # Run forever


class RecordingHTTPServer:
    """HTTP server for browsing and serving recording files."""
    
    def __init__(self, output_dir: Path, host: str = "localhost", port: int = 9826):
        """
        Initialize HTTP server for serving recordings.
        
        Args:
            output_dir: Directory containing recordings
            host: Host to bind to
            port: Port to listen on
        """
        if web is None:
            raise ImportError(
                "aiohttp library is required for RecordingHTTPServer. "
                "Install with: pip install aiohttp"
            )
        
        self.output_dir = output_dir
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_get('/api/recordings', self.list_recordings)
        self.app.router.add_get('/api/recordings/{recording_id}', self.get_recording_files)
        self.app.router.add_get('/api/recordings/{recording_id}/metadata', self.get_metadata)
        # More specific route must come before the general {role} route
        self.app.router.add_get('/api/recordings/{recording_id}/audio/interleaved', self.get_interleaved_audio)
        self.app.router.add_get('/api/recordings/{recording_id}/audio/{role}', self.get_audio)
        # Enable CORS for all routes
        self.app.middlewares.append(self._cors_middleware)
    
    @web.middleware
    async def _cors_middleware(self, request, handler):
        """Add CORS headers to all responses."""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    async def list_recordings(self, request):
        """List all recording directories."""
        try:
            recordings = []
            if self.output_dir.exists():
                for item in sorted(self.output_dir.iterdir(), reverse=True):
                    if item.is_dir():
                        metadata_file = item / "metadata.json"
                        metadata = {}
                        if metadata_file.exists():
                            with open(metadata_file, 'r') as f:
                                metadata = json.load(f)
                        
                        recordings.append({
                            "id": item.name,
                            "path": str(item),
                            "name": item.name,
                            "metadata": metadata
                        })
            
            return web.json_response({
                "recordings": recordings,
                "count": len(recordings)
            })
        
        except Exception as e:
            _logger.error(f"Error listing recordings: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def get_recording_files(self, request):
        """Get list of files in a recording directory."""
        try:
            recording_id = request.match_info['recording_id']
            recording_dir = self.output_dir / recording_id
            
            if not recording_dir.exists() or not recording_dir.is_dir():
                return web.json_response(
                    {"error": "Recording not found"},
                    status=404
                )
            
            files = []
            for item in recording_dir.iterdir():
                if item.is_file():
                    files.append({
                        "name": item.name,
                        "size": item.stat().st_size,
                        "type": item.suffix[1:] if item.suffix else "unknown"
                    })
            
            return web.json_response({
                "recording_id": recording_id,
                "files": files
            })
        
        except Exception as e:
            _logger.error(f"Error getting recording files: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def get_metadata(self, request):
        """Get metadata.json for a recording."""
        try:
            recording_id = request.match_info['recording_id']
            metadata_file = self.output_dir / recording_id / "metadata.json"
            
            if not metadata_file.exists():
                return web.json_response(
                    {"error": "Metadata not found"},
                    status=404
                )
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            return web.json_response(metadata)
        
        except Exception as e:
            _logger.error(f"Error getting metadata: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def get_audio(self, request):
        """Get audio file (user.raw or agent.raw) for a recording."""
        try:
            recording_id = request.match_info['recording_id']
            role = request.match_info['role']
            
            if role not in ['user', 'agent']:
                return web.json_response(
                    {"error": "Invalid role. Must be 'user' or 'agent'"},
                    status=400
                )
            
            audio_file = self.output_dir / recording_id / f"{role}.raw"
            
            if not audio_file.exists():
                return web.json_response(
                    {"error": f"Audio file not found: {role}.raw"},
                    status=404
                )
            
            # Read the raw audio file
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Return raw PCM audio with appropriate headers
            return web.Response(
                body=audio_data,
                content_type='pcm_s16le',
                headers={
                    'Content-Disposition': f'inline; filename="{role}.raw"',
                    'X-Sample-Rate': '16000',
                    'X-Channels': '1',
                    'X-Bit-Depth': '16'
                }
            )
        
        except Exception as e:
            _logger.error(f"Error getting audio: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def get_interleaved_audio(self, request):
        """Get interleaved audio file for a recording."""
        try:
            recording_id = request.match_info['recording_id']
            
            audio_file = self.output_dir / recording_id / "interleave.raw"
            
            if not audio_file.exists():
                return web.json_response(
                    {"error": "Interleaved audio file not found"},
                    status=404
                )
            
            # Read the raw audio file
            with open(audio_file, 'rb') as f:
                audio_data = f.read()
            
            # Return raw PCM audio with appropriate headers
            # Stereo format: both channels contain the same mixed audio (user + agent)
            return web.Response(
                body=audio_data,
                content_type='pcm_s16le',
                headers={
                    'Content-Disposition': 'inline; filename="interleave.raw"',
                    'X-Sample-Rate': '16000',
                    'X-Channels': '2',
                    'X-Bit-Depth': '16',
                    'X-Channel-Layout': 'stereo (both channels mixed)'
                }
            )
        
        except Exception as e:
            _logger.error(f"Error getting interleaved audio: {e}", exc_info=True)
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def start(self):
        """Start the HTTP server."""
        _logger.info(f"Starting HTTP server on http://{self.host}:{self.port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        _logger.info(f"HTTP server listening on http://{self.host}:{self.port}")
        return runner


async def main():
    """Main entry point for standalone server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Determine output directory
    script_dir = Path(__file__).parent
    output_dir = script_dir / "tmp"
    
    # Start WebSocket recording server
    ws_server = RecordingServer(host="localhost", port=9825, output_dir=str(output_dir))
    
    # Start HTTP server for file browsing
    http_server = None
    if web is not None:
        try:
            http_server = RecordingHTTPServer(output_dir=output_dir, host="localhost", port=9826)
            http_runner = await http_server.start()
        except Exception as e:
            _logger.warning(f"Could not start HTTP server: {e}")
    else:
        _logger.warning("aiohttp not installed. HTTP file server will not be available.")
    
    # Start WebSocket server (this blocks)
    await ws_server.start()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
