"""Configuration for the observability tracer.

TracerConfig reads the OTLP endpoint from an environment variable and
exposes only optional overrides to the user.  ``tenant.id`` and
``agent.id`` are read at span-creation time from OpenTelemetry Baggage
(see :class:`BaggageSpanProcessor`).

For external agent runs, TracerConfig can be configured with trace injection
parameters to send traces to the WXO platform via the API proxy endpoint.
Authentication can be provided via AgenticSession or API key.
"""

import os
import logging
import json
import base64
from typing import Any, Optional, Dict, TYPE_CHECKING, Union
from dataclasses import dataclass, field
from urllib.parse import urljoin

if TYPE_CHECKING:
    from ibm_watsonx_orchestrate_sdk.common.session import AgenticSession
    from ibm_watsonx_orchestrate_sdk.client import Client

from ibm_watsonx_orchestrate_sdk.observability.attributes import (
    ENV_OTLP_ENDPOINT,
    DEFAULT_SERVICE_NAME,
)

logger = logging.getLogger(__name__)


@dataclass
class TracerConfig:
    """User-facing configuration for the observability tracer.

    The OTLP endpoint is read from ``WXO_OTLP_ENDPOINT``.
    ``tenant.id`` and ``agent.id`` are propagated via OpenTelemetry
    Baggage and automatically injected into every span by the
    ``BaggageSpanProcessor``.

    Users may optionally override ``service_name`` or supply extra
    ``resource_attributes``.

    For external agent runs, configure trace injection parameters to send
    traces to the WXO platform via the API proxy endpoint. This requires
    builder or admin role permissions. Authentication is provided via
    Client.session (AgenticSession). The trace injection URL is automatically
    constructed as: session.base_url + trace_injection_path

    Args:
        service_name: Service name for the tracer (default: "wxo-agentic-sdk")
        resource_attributes: Additional resource attributes to attach to all spans
        client: Client object for authentication (required for trace injection). Session will be extracted from client.
        trace_injection_path: Partial URL path for trace injection (default: "/inject/traces")
        tenant_id: Tenant identifier for multi-tenancy support (optional, auto-extracted from JWT token if not provided)
        agent_id: Agent identifier
        workspace_id: Workspace identifier
        environment: Deployment environment (default: "live")

    Example:
        # Standard usage with OTLP endpoint from environment (no authentication)
        config = TracerConfig(service_name="my-agent")

        # External agent with trace injection (tenant_id auto-extracted from token)
        from ibm_watsonx_orchestrate import Client
        
        client = Client(api_key="your-key", instance_url="https://instance.example.com")
        
        config = TracerConfig(
            client=client,  # Authentication, instance URL, and tenant_id from client
            agent_id="agent-456",
            workspace_id="workspace-789",
            environment="live"
        )
        # Trace injection URL will be: https://instance.example.com/inject/traces
        # tenant_id will be automatically extracted from the JWT token
        
        # Or explicitly provide tenant_id to override
        config = TracerConfig(
            client=client,
            tenant_id="tenant-123",  # Explicit tenant_id overrides token extraction
            agent_id="agent-456",
            workspace_id="workspace-789",
            environment="live"
        )
        
        # External agent with custom trace injection path
        config = TracerConfig(
            client=client,
            trace_injection_path="/api/v2/traces",  # Override default path
            tenant_id="tenant-123",
            agent_id="agent-456",
            workspace_id="workspace-789",
            environment="live"
        )
        # Trace injection URL will be: https://instance.example.com/api/v2/traces
        
        tracer = Tracer(config)
    """

    service_name: str = DEFAULT_SERVICE_NAME
    resource_attributes: Dict[str, str] = field(default_factory=dict)

    # Authentication via Client
    client: Optional["Client"] = None

    # Trace injection parameters for external agent runs
    trace_injection_path: str = "/inject/traces"  # Partial URL path
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    workspace_id: Optional[str] = None
    environment: str = "live"
    user_id: Optional[str] = None

    # Internal session extracted from client
    _session: Optional["AgenticSession"] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Extract session from client and tenant_id/user_id from token if client is provided."""
        if self.client is not None:
            if hasattr(self.client, 'session'):
                self._session = self.client.session
                logger.debug("Extracted session from client object")
                
                # Extract tenant_id from token if not explicitly provided
                if not self.tenant_id:
                    extracted_tenant_id = self._extract_tenant_id_from_token()
                    if extracted_tenant_id:
                        self.tenant_id = extracted_tenant_id
                        logger.debug(f"Extracted tenant_id from token: {self.tenant_id}")
                
                # Extract user_id from token if not explicitly provided
                if not self.user_id:
                    self.user_id = self._extract_user_id_from_token()
                    logger.debug(f"Extracted user_id from token: {self.user_id}")
            else:
                logger.warning("Client object does not have a session attribute")

    def _extract_tenant_id_from_token(self) -> Optional[str]:
        """Extract tenant_id from JWT token.
        
        Returns:
            Tenant ID if found in token, None otherwise.
        """
        try:
            # Get token from session
            token = None
            if self._session:
                if hasattr(self._session, 'access_token') and self._session.access_token:
                    token = self._session.access_token
                elif hasattr(self._session, 'authenticator'):
                    if hasattr(self._session.authenticator, 'token_manager'):
                        token = self._session.authenticator.token_manager.get_token()  # type: ignore[attr-defined]
                    elif hasattr(self._session.authenticator, 'get_token'):
                        token: Any = self._session.authenticator.get_token()  # type: ignore[attr-defined]
            
            if not token:
                logger.debug("No token available to extract tenant_id")
                return None
            
            # JWT tokens have 3 parts separated by dots: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("Token is not a valid JWT format")
                return None
            
            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed (JWT base64 encoding may not have padding)
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            # Decode base64
            decoded = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded)
            
            # Look for tenant_id in various possible claim names
            tenant_id = (
                payload_data.get('tenant_id') or
                payload_data.get('tenantId') 
            )
            
            if tenant_id:
                logger.debug(f"Found tenant_id in token: {tenant_id}")
                return str(tenant_id)
            else:
                logger.debug("No tenant_id found in token payload")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to extract tenant_id from token: {e}")
            return None

    def _extract_user_id_from_token(self) -> str:
        """Extract user_id from JWT token.
        
        Returns:
            User ID if found in token (from idpUniqueId field), "unknown" otherwise.
        """
        user_id = "unknown"
        
        try:
            # Get token from session
            token = None
            if self._session:
                if hasattr(self._session, 'access_token') and self._session.access_token:
                    token = self._session.access_token
                elif hasattr(self._session, 'authenticator'):
                    if hasattr(self._session.authenticator, 'token_manager'):
                        token = self._session.authenticator.token_manager.get_token()  # type: ignore[attr-defined]
                    elif hasattr(self._session.authenticator, 'get_token'):
                        token: Any = self._session.authenticator.get_token()  # type: ignore[attr-defined]
            
            if not token:
                logger.debug("No token available to extract user_id")
            elif len(token.split('.')) != 3:
                logger.warning("Token is not a valid JWT format")
            else:
                # JWT tokens have 3 parts separated by dots: header.payload.signature
                parts = token.split('.')
                
                # Decode the payload (second part)
                payload = parts[1]
                # Add padding if needed (JWT base64 encoding may not have padding)
                padding = 4 - len(payload) % 4
                if padding != 4:
                    payload += '=' * padding
                
                # Decode base64
                decoded = base64.urlsafe_b64decode(payload)
                payload_data = json.loads(decoded)
                
                # Look for user_id in idpUniqueId claim
                extracted_user_id = payload_data.get('idpUniqueId')
                
                if extracted_user_id:
                    user_id = str(extracted_user_id)
                    logger.debug(f"Found user_id in token: {user_id}")
                else:
                    logger.debug("No idpUniqueId found in token payload")
                
        except Exception as e:
            logger.warning(f"Failed to extract user_id from token: {e}")
        
        return user_id


    @property
    def session(self) -> Optional["AgenticSession"]:
        """Get the session from the client."""
        return self._session

    @property
    def endpoint(self) -> Optional[str]:
        """Get the OTLP endpoint.

        If session is configured, constructs the trace injection URL using
        ``urllib.parse.urljoin(base_url, trace_injection_path)``.

        If ``trace_injection_path`` is already an absolute URL (starts with
        ``http://`` or ``https://``), it is returned as-is.

        Otherwise falls back to the ``WXO_OTLP_ENDPOINT`` environment variable.
        """
        if self.session and self.session.base_url:
            # Already an absolute URL — use directly
            if self.trace_injection_path.startswith(('http://', 'https://')):
                return self.trace_injection_path
            # Ensure base ends with "/" so urljoin appends rather than replaces
            # the last path segment (standard urljoin behaviour).
            base = self.session.base_url.rstrip('/') + '/'
            return urljoin(base, self.trace_injection_path.lstrip('/'))
        return os.environ.get(ENV_OTLP_ENDPOINT)

    @property
    def is_trace_injection_mode(self) -> bool:
        """Check if tracer is configured for trace injection mode.

        Returns:
            True if client is configured (trace injection mode), False otherwise.
        """
        return self.client is not None

    def get_auth_headers(self) -> Dict[str, str]:
        """Extract authentication headers for OTLP exporter from AgenticSession.

        Uses authentication from Client.session:
        - access_token (runs-on, local modes)
        - authenticator (runs-elsewhere mode)

        Returns:
            Dictionary of HTTP headers for authentication.

        Raises:
            RuntimeError: If an authenticator is present but token retrieval fails,
                so the caller (e.g. DynamicAuthOTLPSpanExporter) can decide whether
                to abort the export or fall back to cached credentials.
        """
        headers: Dict[str, str] = {}

        # Get auth from AgenticSession
        if self.session is not None:
            # Use access_token if available (runs-on, local modes)
            if self.session.access_token:
                headers["Authorization"] = f"Bearer {self.session.access_token}"
                logger.debug("Using access_token from AgenticSession for authentication")
                return headers

            # Use authenticator for runs-elsewhere mode
            if self.session.authenticator:
                auth = self.session.authenticator
                token = None
                try:
                    if hasattr(auth, 'token_manager'):
                        token = auth.token_manager.get_token()  # type: ignore[attr-defined]
                    elif hasattr(auth, 'get_token'):
                        token = auth.get_token()  # type: ignore[attr-defined]
                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to retrieve authentication token from authenticator: {exc}"
                    ) from exc

                if token:
                    headers["Authorization"] = f"Bearer {token}"
                    logger.debug("Using authenticator from AgenticSession for authentication")
                    return headers
                else:
                    logger.warning(
                        "Authenticator returned an empty token; "
                        "the OTLP request will be sent without an Authorization header."
                    )

        logger.debug("No authentication configured")
        return headers

    def build_resource_attributes(self) -> Dict[str, str]:
        """Return resource attributes for the TracerProvider.

        Includes trace injection context attributes when configured.
        """
        attrs: Dict[str, str] = {}
        attrs.update(self.resource_attributes)

        # Add trace injection context attributes if configured
        if self.is_trace_injection_mode:
            if self.tenant_id:
                attrs["tenant.id"] = self.tenant_id
            if self.agent_id:
                attrs["agent.id"] = self.agent_id
            if self.workspace_id:
                attrs["workspace.id"] = self.workspace_id
            if self.environment:
                attrs["environment.name"] = self.environment

        return attrs

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If trace injection mode is enabled but required parameters are missing.
        """
        if self.is_trace_injection_mode:
            missing_params = []
            if not self.client:
                missing_params.append("client (Client object required for authentication)")
            if not self.tenant_id:
                missing_params.append("tenant_id")
            if not self.agent_id:
                missing_params.append("agent_id")
            if not self.workspace_id:
                missing_params.append("workspace_id")

            if missing_params:
                raise ValueError(
                    f"Trace injection mode requires the following parameters: "
                    f"{', '.join(missing_params)}"
                )

            # Validate environment value
            valid_environments = ["draft", "live"]
            if self.environment not in valid_environments:
                raise ValueError(
                    f"Invalid environment '{self.environment}'. "
                    f"Must be one of: {', '.join(valid_environments)}"
                )

            logger.info(
                "TracerConfig validated for trace injection mode: "
                f"tenant_id={self.tenant_id}, agent_id={self.agent_id}, "
                f"workspace_id={self.workspace_id}, environment={self.environment}"
            )
