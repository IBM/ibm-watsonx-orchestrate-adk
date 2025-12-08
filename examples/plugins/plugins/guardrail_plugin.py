import re
from enum import Enum
from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.tools.types import PythonToolKind, PluginContext, AgentPreInvokePayload, AgentPreInvokeResult


@tool( description="Pre-invoke plugin that blocks disallowed words and masks sensitive terms in user input before the agent processes it.", kind=PythonToolKind.AGENTPREINVOKE)
def guardrail_plugin(plugin_context: PluginContext, agent_pre_invoke_payload: AgentPreInvokePayload) -> AgentPreInvokeResult:

    user_input = ''
    modified_payload = agent_pre_invoke_payload
    res = AgentPreInvokeResult()
    if agent_pre_invoke_payload and agent_pre_invoke_payload.messages:
        user_input = agent_pre_invoke_payload.messages[-1].content.text


    def mask_words_in_text(text: str, words_to_mask: list, mask_char: str = '*') -> str:
        """
        Masks all occurrences of selected words in a given text.

        Args:
            text (str): The input text.
            words_to_mask (list): List of words (case-insensitive) to mask.
            mask_char (str): Character to use for masking.

        Returns:
            str: The masked text.
        """
        if not words_to_mask:
            return text

        # Escape special regex characters and join words into a regex pattern
        pattern = r'\b(' + '|'.join(map(re.escape, words_to_mask)) + r')\b'

        def mask_match(match):
            word = match.group(0)
            return mask_char * len(word)

        # Replace words, ignoring case
        return re.sub(pattern, mask_match, text, flags=re.IGNORECASE)

    words = [ 'silly', 'Silly']
    if 'stupid' in user_input:
        modified_text = 'blocked'
        res.continue_processing = False
    else:
        modified_text = mask_words_in_text(text=user_input, words_to_mask=words)
        res.continue_processing = True
    modified_payload.messages[-1].content.text = modified_text
    res.modified_payload = modified_payload
    return res





