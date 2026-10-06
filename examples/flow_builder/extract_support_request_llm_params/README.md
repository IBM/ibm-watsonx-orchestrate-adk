### extract_support_request_llm_params

Variant of `extract_support_request` that demonstrates the new `AITaskLLMParameters`
builder introduced for the AI Task prompt node.

Instead of passing a plain dict:

```python
llm_parameters={"temperature": 0, "max_new_tokens": 400, ...}
```

LLM parameters are built with the fluent `AITaskLLMParameters` builder:

```python
from ibm_watsonx_orchestrate.flow_builder.flows import AITaskLLMParameters

llm_params = (
    AITaskLLMParameters()
    .add("temperature", 0.0)
    .add("min_new_tokens", 5)
    .add("max_new_tokens", 400)
    .add("top_k", 1)
    .add("stop_sequences", ["Human:", "AI:"])
    .add("top_p", 0.9, enabled=False)   # defined but currently inactive
)
```

The builder infers `parameter_type` from the Python type of the value and serialises
the result to the structured `parameters[]` payload the runtime expects.

---

### Testing the flow inside an agent

1. Make sure the Flow runtime is activated.
2. Run `import-all.sh`
3. Launch the Chat UI with `orchestrate chat start`
4. Pick the `ticket_processing_agent`
5. Use the sample support request:

   `Can you help process the following support request: Date: Thu, 3 Apr 2025 16:46:52 -0400 From: Jane Stevenson<js@acme.com> To: customer_support@jacket.com I recently ordered a lather jacket from you, but it's been 2 weeks and I have yet to received it. Here is my order number: 2025-03-02-ABC34343. Can you find out what's the current status? Regards, Jane`

### Testing the flow programmatically

1. Set `PYTHONPATH=<ADK>/src:<ADK>` where `<ADK>` is the directory where you downloaded the ADK.
2. Run `python3 main.py`
