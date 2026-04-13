from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Optional

from ibm_cloud_sdk_core.authenticators import Authenticator

from ibm_watsonx_orchestrate_sdk.common.session import (
    AgenticSession,
    ExecutionContext,
    build_local_session,
    build_runs_elsewhere_session,
    build_runs_on_session,
    get_agentic_mode_hint,
)
from ibm_watsonx_orchestrate_sdk.context.context_client import ContextClient
from ibm_watsonx_orchestrate_sdk.memory.memory_client import MemoryClient
from ibm_watsonx_orchestrate_clients.common.utils import is_local_dev
from ibm_watsonx_orchestrate_clients.common.service_instance.local_service_instance import DEFAULT_LOCAL_SERVICE_URL


def _extract_configurable(config: Any) -> Mapping[str, Any]:
    if isinstance(config, Mapping):
        configurable = config.get("configurable", {})
    elif hasattr(config, "get"):
        configurable = config.get("configurable", {})
    else:
        configurable = {}

    if not isinstance(configurable, Mapping):
        raise ValueError("RunnableConfig.configurable must be a mapping")
    return configurable


class Client:
    """Main client for the IBM watsonx Orchestrate Agentic SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        instance_url: Optional[str] = None,
        verify: Optional[str | bool] = None,
        authenticator: Optional[Authenticator] = None,
        local: bool = False,
        *,
        execution_context: Optional[ExecutionContext | Mapping[str, Any]] = None,
        session: Optional[AgenticSession] = None,
    ):
        mode_hint = get_agentic_mode_hint()

        if session is not None:
            self._session = session
        elif execution_context is not None:
            self._session = build_runs_on_session(execution_context, verify=verify)
        else:
            use_env_auth = api_key is None and instance_url is None and authenticator is None
            if use_env_auth and mode_hint == "runs-on":
                raise ValueError(
                    "runs-on mode requires request-scoped execution_context. "
                    "Use Client(execution_context=...) or Client.from_runnable_config(config)."
                )
            if use_env_auth:
                env_token = os.environ.get("WXO_USER_TOKEN")
                env_url = os.environ.get("WXO_AUTH_URL")
                if env_token and env_url:
                    api_key = env_token
                    instance_url = env_url
                    local = True
                elif env_url:
                    # This is valid for a scenario where user is running wxo-server in different port and wish to provide custom instance url
                    instance_url = env_url
                    local = True
                    api_key = None
                else:
                    # No env vars - use default from LocalServiceInstance with auto-generated token
                    instance_url = DEFAULT_LOCAL_SERVICE_URL
                    local = True
                    api_key = None

            if instance_url is None:
                raise ValueError("instance_url is required")

            if not local and instance_url and api_key and authenticator is None and is_local_dev(instance_url):
                local = True

            if local:
                self._session = build_local_session(
                    instance_url=instance_url,
                    access_token=api_key,
                    verify=verify,
                )
            else:
                if api_key is None and authenticator is None:
                    raise ValueError("api_key or authenticator is required")
                self._session = build_runs_elsewhere_session(
                    instance_url=instance_url,
                    api_key=api_key or "",
                    verify=verify,
                    authenticator=authenticator,
                )

        self._context_client: Optional[ContextClient] = None
        self._memory_client: Optional[MemoryClient] = None

    @classmethod
    def from_instance_credentials(
        cls,
        *,
        instance_url: str,
        api_key: str,
        verify: Optional[str | bool] = None,
        authenticator: Optional[Authenticator] = None,
    ) -> "Client":
        session = build_runs_elsewhere_session(
            instance_url=instance_url,
            api_key=api_key,
            verify=verify,
            authenticator=authenticator,
        )
        return cls(session=session)

    @classmethod
    def from_execution_context(
        cls,
        execution_context: ExecutionContext | Mapping[str, Any],
        *,
        verify: Optional[str | bool] = None,
    ) -> "Client":
        session = build_runs_on_session(execution_context, verify=verify)
        return cls(session=session)

    @classmethod
    def from_runnable_config(
        cls,
        config: Any,
        *,
        verify: Optional[str | bool] = None,
    ) -> "Client":
        configurable = _extract_configurable(config)
        execution_context = configurable.get("execution_context")
        if not isinstance(execution_context, Mapping):
            raise ValueError("RunnableConfig is missing configurable.execution_context")
        return cls(execution_context=execution_context, verify=verify)

    @property
    def session(self) -> AgenticSession:
        return self._session

    @property
    def context(self) -> ContextClient:
        if self._context_client is None:
            self._context_client = ContextClient(self._session)
        return self._context_client

    @property
    def memory(self) -> MemoryClient:
        if self._memory_client is None:
            self._memory_client = MemoryClient(self._session)
        return self._memory_client


AgenticSDK = Client
