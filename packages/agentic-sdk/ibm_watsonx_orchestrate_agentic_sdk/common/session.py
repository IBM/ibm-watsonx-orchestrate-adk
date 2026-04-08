from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Literal, Mapping, Optional, TypedDict

import jwt
from ibm_cloud_sdk_core.authenticators import Authenticator

from ibm_watsonx_orchestrate_clients.common.credentials import Credentials
from ibm_watsonx_orchestrate_clients.common.service_instance.service_instance import ServiceInstance

AgenticMode = Literal["runs-on", "runs-elsewhere", "local"]


class ExecutionContext(TypedDict, total=False):
    access_token: str
    api_proxy_url: str
    tenant_id: str
    user_id: str
    thread_id: str
    run_id: str
    deployment_platform: str


@dataclass(frozen=True)
class RequestIdentity:
    tenant_id: str | None
    user_id: str | None
    thread_id: str
    run_id: str | None = None
    deployment_platform: str | None = None


@dataclass(frozen=True)
class AgenticSession:
    mode: AgenticMode
    base_url: str
    verify: str | bool | None = None
    access_token: str | None = None
    authenticator: Authenticator | None = None
    identity: RequestIdentity | None = None


class _DummyClient:
    """Dummy client for ServiceInstance initialization."""

    def __init__(self, credentials: Credentials):
        self.credentials = credentials
        self.token = None


def get_agentic_mode_hint() -> AgenticMode | None:
    mode_hint = str(os.environ.get("WXO_AGENTIC_MODE") or "").strip()
    if mode_hint in {"runs-on", "runs-elsewhere", "local"}:
        return mode_hint  # type: ignore[return-value]
    return None


def get_runs_on_default_api_proxy_url() -> str:
    return str(os.environ.get("WXO_API_PROXY_URL") or "").rstrip("/")


def get_runs_on_default_deployment_platform() -> str | None:
    deployment_platform = str(os.environ.get("DEPLOYMENT_PLATFORM") or "").strip()
    return deployment_platform or None


def normalize_access_token(token: str) -> str:
    if not token:
        raise ValueError("access token is required")
    if token.startswith("Bearer "):
        return token.removeprefix("Bearer ").strip()
    return token.strip()


def decode_jwt_claims(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return {}
    if isinstance(claims, dict):
        return claims
    return {}


def get_claim_value(claims: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = claims.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def build_runs_on_session(
    execution_context: Mapping[str, Any],
    *,
    verify: str | bool | None = None,
) -> AgenticSession:
    access_token = normalize_access_token(str(execution_context.get("access_token") or ""))
    api_proxy_url = str(
        execution_context.get("api_proxy_url") or get_runs_on_default_api_proxy_url()
    ).rstrip("/")
    thread_id = str(execution_context.get("thread_id") or "").strip()
    mode_hint = get_agentic_mode_hint()

    if not api_proxy_url:
        if mode_hint == "runs-on":
            raise ValueError(
                "runs-on mode requires execution_context.api_proxy_url or WXO_API_PROXY_URL"
            )
        raise ValueError("execution_context.api_proxy_url is required")
    if not thread_id:
        raise ValueError("execution_context.thread_id is required")

    claims = decode_jwt_claims(access_token)
    tenant_id = str(
        execution_context.get("tenant_id")
        or get_claim_value(claims, "woTenantId", "tenant_id", "tenantId")
        or ""
    ).strip() or None
    user_id = str(
        execution_context.get("user_id")
        or get_claim_value(claims, "woUserId", "user_id", "userId", "sub")
        or ""
    ).strip() or None
    run_id = str(execution_context.get("run_id") or "").strip() or None
    deployment_platform = str(
        execution_context.get("deployment_platform") or get_runs_on_default_deployment_platform() or ""
    ).strip() or None

    return AgenticSession(
        mode="runs-on",
        base_url=api_proxy_url,
        verify=verify,
        access_token=access_token,
        identity=RequestIdentity(
            tenant_id=tenant_id,
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            deployment_platform=deployment_platform,
        ),
    )


def build_runs_elsewhere_session(
    *,
    instance_url: str,
    api_key: str,
    verify: str | bool | None = None,
    authenticator: Authenticator | None = None,
) -> AgenticSession:
    if not instance_url:
        raise ValueError("instance_url is required")
    if not api_key and authenticator is None:
        raise ValueError("api_key is required")

    credentials = Credentials(url=instance_url, api_key=api_key, verify=verify)
    resolved_authenticator = authenticator
    if resolved_authenticator is None:
        dummy_client = _DummyClient(credentials)
        service_instance = ServiceInstance(dummy_client)
        resolved_authenticator = service_instance._get_authenticator(service_instance._infer_auth_type())

    return AgenticSession(
        mode="runs-elsewhere",
        base_url=f"{instance_url.rstrip('/')}/v1/orchestrate",
        verify=verify,
        authenticator=resolved_authenticator,
    )


def build_local_session(
    *,
    instance_url: str,
    access_token: str,
    verify: str | bool | None = None,
) -> AgenticSession:
    if not instance_url:
        raise ValueError("instance_url is required")

    return AgenticSession(
        mode="local",
        base_url=f"{instance_url.rstrip('/')}/api/v1",
        verify=verify,
        access_token=normalize_access_token(access_token),
    )
