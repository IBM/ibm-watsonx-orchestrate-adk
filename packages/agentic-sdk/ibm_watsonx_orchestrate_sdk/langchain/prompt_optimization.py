"""LangGraph prompt optimization wrapper.

Usage::

    from ibm_watsonx_orchestrate_sdk import Client
    from ibm_watsonx_orchestrate_sdk.langchain import prompt_optimization_manager_for_langgraph

    client = Client(instance_url="...", api_key="...")
    graph = prompt_optimization_manager_for_langgraph(
        create_react_agent(llm, tools),
        default_prompt="You are an IT support agent...",
        agent_id="ae90579a-...",
        client=client,
    )

    # Use normally — prompt is auto-injected
    graph.invoke({"messages": [("user", "Reset my password")]})
"""

from __future__ import annotations

import logging
import re
from langchain_core.messages import AIMessage, SystemMessage

from ibm_watsonx_orchestrate_sdk.client import Client
from ibm_watsonx_orchestrate_sdk.prompt.prompt_client import PromptClient

logger = logging.getLogger(__name__)

_SYSTEM_MSG_ID = "agentops-system-prompt"

_KNOWN_DIRECTIVES = {
    "get-prompt",
    "refresh-prompt",
    "optimization-run-id",
}
_DIRECTIVE_RE = re.compile(
    r"\[agentops:(" + "|".join(re.escape(d) for d in _KNOWN_DIRECTIVES) + r")(?:=([^\]]*))?\]"
)


def prompt_optimization_manager_for_langgraph(
    graph,
    default_prompt: str,
    *,
    agent_id: str,
    client: Client,
):
    prompt_client = PromptClient(client.session, agent_id)
    return _ManagedGraph(graph, default_prompt, prompt_client)


class _ManagedGraph:

    def __init__(self, graph, default_prompt: str, prompt_client: PromptClient) -> None:
        self._graph = graph
        self._default = default_prompt
        self._client = prompt_client
        self._client.connect()
        self._client.load_active_prompt()

    @property
    def default_prompt(self) -> str:
        return self._default

    def invoke(self, input, config=None, **kwargs):
        short = self._try_short_circuit(input)
        if short is not None:
            return short
        return self._graph.invoke(self._inject(input, config), config, **kwargs)

    def stream(self, input, config=None, **kwargs):
        short = self._try_short_circuit(input)
        if short is not None:
            yield short
            return
        yield from self._graph.stream(self._inject(input, config), config, **kwargs)

    async def ainvoke(self, input, config=None, **kwargs):
        short = self._try_short_circuit(input)
        if short is not None:
            return short
        return await self._graph.ainvoke(self._inject(input, config), config, **kwargs)

    async def astream(self, input, config=None, **kwargs):
        short = self._try_short_circuit(input)
        if short is not None:
            yield short
            return
        async for event in self._graph.astream(self._inject(input, config), config, **kwargs):
            yield event

    def __getattr__(self, name):
        # Delegate attribute access to the wrapped graph so callers can treat
        # _ManagedGraph as a drop-in replacement (e.g. graph.get_graph()).
        return getattr(self._graph, name)

    def __dir__(self):
        return list(set(super().__dir__()) | set(dir(self._graph)))

    def _try_short_circuit(self, input) -> dict | None:
        messages = input.get("messages", [])
        if not messages:
            return None
        text = _get_text(messages[-1])
        if text and "[agentops:get-prompt]" in text:
            prompt = self._client.active_prompt or self._default
            return {"messages": [AIMessage(content=prompt)]}

    def _inject(self, input, config):
        messages = list(input.get("messages", []))
        directives = _extract_directives(messages)

        if "refresh-prompt" in directives:
            self._client.load_active_prompt()

        instructions = self._resolve_prompt(config, directives)
        sys_msg = SystemMessage(content=instructions, id=_SYSTEM_MSG_ID)
        if messages and _is_system(messages[0]):
            messages[0] = sys_msg
        else:
            messages.insert(0, sys_msg)
        return {**input, "messages": messages}

    def _resolve_prompt(self, config, directives: dict[str, str | None]) -> str:
        run_id = directives.get("optimization-run-id")
        if run_id:
            candidate = self._client.fetch_candidate(run_id)
            if candidate:
                logger.debug("resolve candidate: %s", candidate)
                return candidate

        if self._client.active_prompt:
            return self._client.active_prompt
        return self._default


def _get_text(msg) -> str | None:
    """Extract text content from a message in any supported format."""
    if isinstance(msg, (tuple, list)) and len(msg) >= 2:
        return str(msg[1])
    if hasattr(msg, "content"):
        return str(msg.content)
    if isinstance(msg, dict):
        return msg.get("content") or msg.get("text")
    return None


def _set_text(messages: list, idx: int, new_text: str) -> None:
    """Replace the text content of a message in-place."""
    msg = messages[idx]
    if isinstance(msg, (tuple, list)):
        messages[idx] = (msg[0], new_text, *msg[2:])
    elif hasattr(msg, "content"):
        msg.content = new_text
    elif isinstance(msg, dict):
        if "content" in msg:
            msg["content"] = new_text
        elif "text" in msg:
            msg["text"] = new_text


def _extract_directives(messages: list) -> dict[str, str | None]:
    """Extract [agentops:...] directives from the last message and strip them."""
    if not messages:
        return {}
    idx = len(messages) - 1
    text = _get_text(messages[idx])
    if not text:
        return {}
    matches = list(_DIRECTIVE_RE.finditer(text))
    if not matches:
        return {}
    directives: dict[str, str | None] = {}
    for m in matches:
        directives[m.group(1)] = m.group(2)
    cleaned = _DIRECTIVE_RE.sub("", text).strip()
    if cleaned:
        _set_text(messages, idx, cleaned)
    else:
        messages.pop(idx)
    return directives


def _is_system(msg) -> bool:
    if isinstance(msg, SystemMessage):
        return True
    if isinstance(msg, (tuple, list)) and len(msg) >= 2 and msg[0] == "system":
        return True
    return False
