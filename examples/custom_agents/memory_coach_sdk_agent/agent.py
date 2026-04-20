from __future__ import annotations

import json
import os
from typing import Annotated, Any, Literal, TypedDict

import requests
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import RunnableConfig

from ibm_watsonx_orchestrate_sdk import Client


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-4.1-mini"
MEMORY_LIMIT = 6
MAX_CONTEXT_MEMORIES = 4
APP_NAME = "memory_coach_sdk_agent"


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class MemoryPlan(TypedDict):
    should_search: bool
    should_store: bool
    search_query: str
    memory_type: Literal["profile_fact", "preference", "outcome", "conversational"]
    fact_to_store: str | None
    reasoning: str


def _latest_user_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


def _recent_conversation(messages: list[BaseMessage], limit: int = 8) -> list[dict[str, str]]:
    turns: list[dict[str, str]] = []
    for message in messages[-limit:]:
        content = getattr(message, "content", "")
        if not isinstance(content, str) or not content.strip():
            continue

        message_type = getattr(message, "type", "")
        if message_type == "human":
            role = "user"
        elif message_type == "ai":
            role = "assistant"
        else:
            continue

        turns.append({"role": role, "content": content.strip()})
    return turns


def _format_memory_results(search_response: Any) -> str:
    results = getattr(search_response, "results", [])
    if not results:
        return "No relevant memory found."

    lines: list[str] = []
    for index, result in enumerate(results[:MAX_CONTEXT_MEMORIES], start=1):
        content = getattr(result, "content", "").strip()
        memory_type = getattr(result, "memory_type", None)
        score = getattr(result, "score", None)
        type_fragment = f" [{memory_type}]" if memory_type else ""
        score_fragment = f" score={score:.3f}" if isinstance(score, (float, int)) else ""
        lines.append(f"{index}. {content}{type_fragment}{score_fragment}")
    return "\n".join(lines)


def _openrouter_chat(messages: list[dict[str, str]], *, temperature: float = 0.2) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/IBM/wxo-clients",
            "X-Title": "memory_coach_sdk_agent",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": temperature,
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"].strip()


def _plan_memory_action(user_message: str, recent_turns: list[dict[str, str]]) -> MemoryPlan:
    planning_messages = [
        {
            "role": "system",
            "content": (
                "You are a memory planning assistant for a personalized chat agent. "
                "Decide whether the latest user message should search memory, store memory, or both. "
                "Return JSON only with keys: should_search, should_store, search_query, memory_type, fact_to_store, reasoning. "
                "Valid memory_type values are exactly: profile_fact, preference, outcome, conversational. "
                "Only set fact_to_store when there is a concrete user fact, preference, or outcome worth persisting."
            ),
        },
        *recent_turns,
        {
            "role": "user",
            "content": f"Latest user message:\n{user_message}",
        },
    ]

    raw = _openrouter_chat(planning_messages, temperature=0.0)
    plan_data = json.loads(raw)

    memory_type = str(plan_data.get("memory_type") or "conversational").strip().lower()
    if memory_type not in {"profile_fact", "preference", "outcome", "conversational"}:
        memory_type = "conversational"

    return {
        "should_search": bool(plan_data.get("should_search", False)),
        "should_store": bool(plan_data.get("should_store", False)),
        "search_query": str(plan_data.get("search_query") or user_message).strip() or user_message,
        "memory_type": memory_type,  # type: ignore[return-value]
        "fact_to_store": (
            str(plan_data["fact_to_store"]).strip()
            if plan_data.get("fact_to_store")
            else None
        ),
        "reasoning": str(plan_data.get("reasoning") or "").strip(),
    }


def _search_memory(client: Client, query: str, memory_type: str) -> tuple[bool, str]:
    try:
        result = client.memory.search(
            query=query,
            limit=MEMORY_LIMIT,
            memory_type=memory_type,
            recall=True,
        )
        return True, _format_memory_results(result)
    except Exception as exc:
        return False, _format_memory_error(exc, action="Memory search")


def _format_memory_error(exc: Exception, *, action: str) -> str:
    message = str(exc).strip()

    if isinstance(exc, ValueError) and message:
        return f"{action} failed: {message}"

    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    if isinstance(status_code, int) and 400 <= status_code < 500 and message:
        return f"{action} failed: {message}"

    return f"{action} unavailable."


def _store_memory(client: Client, fact: str, memory_type: str) -> tuple[bool, str | None, str | None]:
    try:
        created = client.memory.add_messages(
            messages=[{"role": "user", "content": fact}],
            infer=False,
            memory_type=memory_type,
            metadata={
                "source": APP_NAME,
                "capture_mode": "llm_planned",
            },
        )
        memories = getattr(created, "memories", [])
        if memories:
            return True, getattr(memories[0], "mem0_id", None), None
        return True, None, None
    except Exception as exc:
        return False, None, _format_memory_error(exc, action="Memory write")


def _build_reply(
    *,
    user_message: str,
    recent_turns: list[dict[str, str]],
    memory_context: str,
    store_status: str,
) -> str:
    response_messages = [
        {
            "role": "system",
            "content": (
                "You are a warm, capable personal assistant. "
                "Use the supplied memory context to personalize your answer, but do not invent memories. "
                "If memory context is empty or unavailable, continue helpfully without claiming certainty. "
                "Keep the answer natural and conversational, not robotic. "
                "If the user shared a new personal detail, subtly acknowledge that you will remember it when appropriate."
            ),
        },
        *recent_turns,
        {
            "role": "user",
            "content": (
                f"Latest user message:\n{user_message}\n\n"
                f"Relevant memory context:\n{memory_context}\n\n"
                f"Memory write status:\n{store_status}"
            ),
        },
    ]
    return _openrouter_chat(response_messages, temperature=0.5)


def create_agent(config: RunnableConfig):
    client = Client.from_runnable_config(config)

    def agent_node(state: AgentState):
        messages = state.get("messages", [])
        user_message = _latest_user_message(messages)
        if not user_message:
            return {
                "messages": [
                    AIMessage(content="I didn’t receive a user message in this turn.")
                ]
            }

        recent_turns = _recent_conversation(messages)
        planning_error = False
        try:
            plan = _plan_memory_action(user_message, recent_turns)
        except Exception:
            planning_error = True
            plan = {
                "should_search": True,
                "should_store": False,
                "search_query": user_message,
                "memory_type": "conversational",
                "fact_to_store": None,
                "reasoning": "Fallback plan due to planning failure.",
            }

        memory_context = "No memory lookup performed."
        if plan["should_search"]:
            search_ok, memory_context = _search_memory(
                client,
                query=plan["search_query"],
                memory_type=plan["memory_type"],
            )

        store_status = "No memory stored this turn."
        if plan["should_store"] and plan["fact_to_store"]:
            store_ok, memory_id, store_error = _store_memory(
                client,
                fact=plan["fact_to_store"],
                memory_type=plan["memory_type"],
            )
            if store_ok and memory_id:
                store_status = f"Stored successfully as memory id {memory_id}."
            elif store_ok:
                store_status = "Stored successfully."
            else:
                store_status = store_error or "Memory write unavailable."

        try:
            reply = _build_reply(
                user_message=user_message,
                recent_turns=recent_turns,
                memory_context=memory_context,
                store_status=store_status,
            )
        except Exception:
            fallback_parts = []
            if memory_context and memory_context not in {
                "No memory lookup performed.",
                "Memory search unavailable.",
                "No relevant memory found.",
            } and not memory_context.startswith("Memory search failed:"):
                fallback_parts.append("I used what I remember about you to guide this reply.")
            if plan["should_store"] and plan["fact_to_store"] and "Stored successfully" in store_status:
                fallback_parts.append("I’ll keep that in mind for future conversations.")
            if planning_error:
                fallback_parts.append("I had to use a simpler response path this turn.")
            fallback_parts.append(f"You said: {user_message}")
            reply = " ".join(fallback_parts)

        return {"messages": [AIMessage(content=reply)]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    return builder.compile()

# Made with Bob
