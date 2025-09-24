from enum import Enum

class MCPTransportTypes(str, Enum):
    STDIO = "stdio"
    HTTP_STREAMABLE = "http"
    SSE = "sse"