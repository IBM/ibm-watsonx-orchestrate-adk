__all__ = [
    "ChatWxO",
    "WxOEmbeddings",
    "prompt_optimization_manager_for_langgraph",
]


def __getattr__(name: str):
    if name == "ChatWxO":
        from ibm_watsonx_orchestrate_sdk.langchain.chat_models import ChatWxO

        return ChatWxO
    if name == "WxOEmbeddings":
        from ibm_watsonx_orchestrate_sdk.langchain.embeddings import WxOEmbeddings

        return WxOEmbeddings
    if name == "prompt_optimization_manager_for_langgraph":
        from ibm_watsonx_orchestrate_sdk.langchain.prompt_optimization import (
            prompt_optimization_manager_for_langgraph,
        )

        return prompt_optimization_manager_for_langgraph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")