import pytest
from ibm_watsonx_orchestrate.agent_builder.agents import AgentStyle
from ibm_watsonx_orchestrate.agent_builder.agents.types import (
    AgentSpec,
    AgentKind,
    ChatWithDocsConfig,
)
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import (
    CitationsConfig,
    ConfidenceThresholds,
    GenerationConfiguration,
    GeneratedResponseLength,
    HAPFiltering,
    HAPFilteringConfig,
    QueryRewriteConfig,
    QuerySource,
    RetrievalConfidenceThreshold,
    ResponseConfidenceThreshold,
)
from ibm_watsonx_orchestrate.utils.exceptions import BadRequest


def _base_customer_care_spec(**kwargs):
    return {
        "spec_version": "v1",
        "kind": AgentKind.NATIVE,
        "name": "test_cc_agent",
        "description": "A customer care agent",
        "style": AgentStyle.CUSTOMER_CARE,
        **kwargs,
    }


def _base_default_spec(**kwargs):
    return {
        "spec_version": "v1",
        "kind": AgentKind.NATIVE,
        "name": "test_agent",
        "description": "A default agent",
        "style": AgentStyle.DEFAULT,
        **kwargs,
    }


def test_customer_care_with_knowledge_base_does_not_raise():
    """knowledge_base should be accepted for experimental_customer_care style agents."""
    spec = _base_customer_care_spec(knowledge_base=["my_kb"])
    # Should not raise
    agent = AgentSpec(**spec)
    assert agent.knowledge_base == ["my_kb"]


def test_customer_care_without_knowledge_base_does_not_raise():
    """Baseline: customer care agents with no knowledge_base still validate cleanly."""
    spec = _base_customer_care_spec()
    agent = AgentSpec(**spec)
    assert agent.knowledge_base == []


def test_customer_care_tools_still_blocked():
    """Sanity-check: tools remain unsupported for customer care style agents."""
    spec = _base_customer_care_spec(tools=["some_tool"])
    with pytest.raises(BadRequest, match="tools"):
        AgentSpec(**spec)


# ── chat_with_docs / knowledge search ────────────────────────────────────────

def test_chat_with_docs_basic():
    """Default-style agent accepts a basic chat_with_docs config."""
    cwd = ChatWithDocsConfig()
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs is not None
    assert agent.knowledge_base == ["my_kb"]


def test_chat_with_docs_query_source_session_history():
    """chat_with_docs can be set to use session history as the query source."""
    cwd = ChatWithDocsConfig(query_source=QuerySource.SessionHistory)
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.query_source == QuerySource.SessionHistory


def test_chat_with_docs_agent_query_description():
    """Custom agent_query_description is stored on the config."""
    cwd = ChatWithDocsConfig(agent_query_description="Search the product catalog")
    spec = _base_default_spec(knowledge_base=["catalog_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.agent_query_description == "Search the product catalog"


def test_chat_with_docs_confidence_thresholds():
    """Retrieval and response confidence thresholds are stored correctly."""
    thresholds = ConfidenceThresholds(
        retrieval_confidence_threshold=RetrievalConfidenceThreshold.Low,
        response_confidence_threshold=ResponseConfidenceThreshold.High,
    )
    cwd = ChatWithDocsConfig(confidence_thresholds=thresholds)
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    ct = agent.chat_with_docs.confidence_thresholds
    assert ct.retrieval_confidence_threshold == RetrievalConfidenceThreshold.Low
    assert ct.response_confidence_threshold == ResponseConfidenceThreshold.High


def test_chat_with_docs_query_rewrite():
    """Query rewrite config is stored correctly."""
    qr = QueryRewriteConfig(enabled=True, model_id="watsonx/openai/gpt-oss-120b")
    cwd = ChatWithDocsConfig(query_rewrite=qr)
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.query_rewrite.enabled is True
    assert agent.chat_with_docs.query_rewrite.model_id == "watsonx/openai/gpt-oss-120b"


def test_chat_with_docs_generation_config():
    """Generation configuration is stored correctly."""
    gen = GenerationConfiguration(
        model_id="watsonx/openai/gpt-oss-120b",
        prompt_instruction="Respond in English.",
        max_docs_passed_to_llm=5,
        generated_response_length=GeneratedResponseLength.Concise,
        idk_message="I don't know.",
        enabled=True,
    )
    cwd = ChatWithDocsConfig(generation=gen)
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    g = agent.chat_with_docs.generation
    assert g.model_id == "watsonx/openai/gpt-oss-120b"
    assert g.max_docs_passed_to_llm == 5
    assert g.generated_response_length == GeneratedResponseLength.Concise
    assert g.idk_message == "I don't know."
    assert g.enabled is True


def test_chat_with_docs_citations():
    """Citations config is stored correctly."""
    cit = CitationsConfig(citation_title="Sources", citations_shown=3)
    cwd = ChatWithDocsConfig(citations=cit)
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.citations.citation_title == "Sources"
    assert agent.chat_with_docs.citations.citations_shown == 3


def test_chat_with_docs_hap_filtering():
    """HAP filtering config is stored correctly."""
    hap = HAPFiltering(output=HAPFilteringConfig(enabled=True, threshold=0.7))
    cwd = ChatWithDocsConfig(hap_filtering=hap)
    spec = _base_default_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.hap_filtering.output.enabled is True
    assert agent.chat_with_docs.hap_filtering.output.threshold == 0.7


def test_multiple_knowledge_bases():
    """An agent can reference multiple knowledge bases."""
    spec = _base_default_spec(knowledge_base=["kb_one", "kb_two", "kb_three"])
    agent = AgentSpec(**spec)
    assert agent.knowledge_base == ["kb_one", "kb_two", "kb_three"]


def test_customer_care_chat_with_docs_enabled_true_raises():
    """customer_care agents raise when chat_with_docs.enabled is True."""
    cwd = ChatWithDocsConfig(enabled=True)
    spec = _base_customer_care_spec(chat_with_docs=cwd)
    with pytest.raises(BadRequest, match="chat_with_docs.enabled"):
        AgentSpec(**spec)


def test_customer_care_chat_with_docs_enabled_false_does_not_raise():
    """customer_care agents accept chat_with_docs when enabled is not True."""
    cwd = ChatWithDocsConfig(enabled=False)
    spec = _base_customer_care_spec(chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.enabled is False


def test_customer_care_chat_with_docs_enabled_none_does_not_raise():
    """customer_care agents accept chat_with_docs when enabled is None (default)."""
    cwd = ChatWithDocsConfig()
    spec = _base_customer_care_spec(knowledge_base=["my_kb"], chat_with_docs=cwd)
    agent = AgentSpec(**spec)
    assert agent.chat_with_docs.enabled is None