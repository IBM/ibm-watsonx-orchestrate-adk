"""Configuration for the observability tracer.

TracerConfig reads the OTLP endpoint from an environment variable and
exposes only optional overrides to the user.  ``tenant.id`` and
``agent.id`` are read at span-creation time from OpenTelemetry Baggage
(see :class:`BaggageSpanProcessor`).

For external agent runs, TracerConfig can be configured with trace injection
parameters to send traces to the WXO platform via the API proxy endpoint.
"""

import os
import logging
from typing import Optional, Dict
from dataclasses import dataclass, field

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
    builder or admin role permissions.

    Args:
        service_name: Service name for the tracer (default: "wxo-agentic-sdk")
        resource_attributes: Additional resource attributes to attach to all spans
        trace_injection_url: URL endpoint for trace injection via API proxy
        api_key: Authentication key for trace injection endpoint (builder/admin only)
        tenant_id: Tenant identifier for multi-tenancy support
        agent_id: Agent identifier
        workspace_id: Workspace identifier
        environment: Deployment environment (default: "live")

    Example:
        # Standard usage with OTLP endpoint from environment
        config = TracerConfig(service_name="my-agent")

        # External agent with trace injection
        config = TracerConfig(
            trace_injection_url="https://api.example.com/v1/observability/trace-injection",
            api_key="your-api-key",
            tenant_id="tenant-123",
            agent_id="agent-456",
            workspace_id="workspace-789",
            environment="live"
        )
    """

    service_name: str = DEFAULT_SERVICE_NAME
    resource_attributes: Dict[str, str] = field(default_factory=dict)

    # Trace injection parameters for external agent runs
    trace_injection_url: Optional[str] = None
    api_key: Optional[str] = None
    tenant_id: Optional[str] = None
    agent_id: Optional[str] = None
    workspace_id: Optional[str] = None
    environment: str = "live"

    @property
    def endpoint(self) -> Optional[str]:
        """Get the OTLP endpoint.

        Returns trace_injection_url if configured, otherwise falls back to
        WXO_OTLP_ENDPOINT environment variable.
        """
        if self.trace_injection_url:
            return self.trace_injection_url
        return os.environ.get(ENV_OTLP_ENDPOINT)

    @property
    def is_trace_injection_mode(self) -> bool:
        """Check if tracer is configured for trace injection mode.

        Returns:
            True if trace_injection_url is configured, False otherwise.
        """
        return self.trace_injection_url is not None

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
            if not self.api_key:
                missing_params.append("api_key")
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
