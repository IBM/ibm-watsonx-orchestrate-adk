from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import RunnableConfig

from ibm_watsonx_orchestrate_sdk import Client


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def _latest_user_message(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content
    return ""


def _looks_like_question(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False
    if normalized.endswith("?"):
        return True
    return normalized.startswith(
        (
            "what",
            "who",
            "when",
            "where",
            "why",
            "how",
            "do ",
            "does ",
            "did ",
            "can ",
            "could ",
            "would ",
            "should ",
            "is ",
            "are ",
            "was ",
            "were ",
            "tell me",
        )
    )


def _format_search_results(search_response) -> str:
    result_lines = [
        f"{index}. [{result.mem0_id}] score={result.score} {result.content}"
        for index, result in enumerate(search_response.results, start=1)
    ]
    return "\n".join(result_lines)


def create_agent(config: RunnableConfig):
    configurable = config.get("configurable", {})
    execution_context = configurable.get("execution_context", {}) or {}
    client = Client(execution_context=execution_context)

    def agent_node(state: AgentState):
        query = _latest_user_message(state.get("messages", []))
        if not query:
            response_text = "No user message was available in the current thread."
            return {"messages": [AIMessage(content=response_text)]}

        formatted_results = ""
        memory_search_failed = False
        memory_write_failed = False

        try:
            search_response = client.memory.search(query=query, limit=3)
            formatted_results = _format_search_results(search_response)
        except Exception:
            memory_search_failed = True

        if _looks_like_question(query):
            if memory_search_failed:
                response_text = (
                    "I couldn't access memory right now. "
                    "Please try again in a moment."
                )
            elif formatted_results:
                response_text = "I found these relevant memories:\n" + formatted_results
            else:
                response_text = (
                    "I don't remember anything relevant yet. "
                    "Tell me something about yourself and I'll remember it."
                )
        elif formatted_results:
            response_text = "I'll remember that. Related memories:\n" + formatted_results
        else:
            response_text = "I'll remember that for later."

        try:
            client.memory.add_messages(
                messages=[
                    {"role": "user", "content": query},
                ],
                infer=False,
            )
        except Exception:
            memory_write_failed = True

        if memory_write_failed and not _looks_like_question(query):
            response_text = (
                "I heard that, but I couldn't save it to memory right now. "
                "Please try again in a moment."
            )

        return {"messages": [AIMessage(content=response_text)]}

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    return builder.compile()
