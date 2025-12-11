import re
from enum import Enum
from typing import Generic, Optional, Any, List, Dict, TypeAlias, TypeVar, Union, Literal
from pydantic import BaseModel, Field, PrivateAttr, RootModel
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.tools.types import PythonToolKind, PluginContext, AgentPostInvokePayload, \
    AgentPostInvokeResult, TextContent, Message


@tool(description="Post-invoke plugin that detects and masks email addresses in agent responses to protect sensitive information", kind=PythonToolKind.AGENTPOSTINVOKE)
def email_masking_plugin(plugin_context: PluginContext, agent_post_invoke_payload: AgentPostInvokePayload) -> AgentPostInvokeResult:
    result = AgentPostInvokeResult()

    def mask_emails_in_text(text: str, mask_char: str = '*') -> str:
        """
        Finds and masks all email addresses in a given text.
        """
        def mask_email(match):
            email = match.group(0)
            local, domain = email.split('@', 1)
            visible = min(2, len(local))
            masked_local = local[:visible] + mask_char * (len(local) - visible)
            return f"{masked_local}@{domain}"

        email_pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
        return re.sub(email_pattern, mask_email, text)

    if agent_post_invoke_payload is None or agent_post_invoke_payload.messages is None or len(agent_post_invoke_payload.messages) == 0:
        result.continue_processing = False
        return result

    first_msg = agent_post_invoke_payload.messages[0]
    content = getattr(first_msg, "content", None)

    if content is None or not hasattr(content, "text") or content.text is None:
        result.continue_processing = False
        return result

    masked_text = mask_emails_in_text(content.text)
    new_content = TextContent(type="text", text=masked_text)
    new_message = Message(role=first_msg.role, content=new_content)

    modified_payload = agent_post_invoke_payload.copy(deep=True)
    modified_payload.messages[0] = new_message

    result.continue_processing = True
    result.modified_payload = modified_payload

    return result
