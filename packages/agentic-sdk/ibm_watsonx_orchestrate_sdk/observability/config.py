"""Configuration for the observability tracer.

TracerConfig reads the OTLP endpoint from an environment variable and
exposes only optional overrides to the user.  ``tenant.id`` and
``agent.id`` are read at span-creation time from OpenTelemetry Baggage
(see :class:`BaggageSpanProcessor`).
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
    """

    service_name: str = DEFAULT_SERVICE_NAME
    resource_attributes: Dict[str, str] = field(default_factory=dict)

    @property
    def endpoint(self) -> Optional[str]:
        return os.environ.get(ENV_OTLP_ENDPOINT)

    def build_resource_attributes(self) -> Dict[str, str]:
        """Return resource attributes for the TracerProvider."""
        attrs: Dict[str, str] = {}
        attrs.update(self.resource_attributes)
        return attrs
