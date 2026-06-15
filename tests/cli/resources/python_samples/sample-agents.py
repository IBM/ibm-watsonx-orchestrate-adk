from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.knowledge_base import KnowledgeBase
from ibm_watsonx_orchestrate.agent_builder.knowledge_bases.types import ConversationalSearchConfig, IndexConnection, MilvusConnection, FieldMapping
from ibm_watsonx_orchestrate.agent_builder.agents.agent import Agent
from ibm_watsonx_orchestrate.agent_builder.agents.external_agent import ExternalAgent
from ibm_watsonx_orchestrate.agent_builder.agents.assistant_agent import AssistantAgent
from ibm_watsonx_orchestrate.agent_builder.agents.types import AgentStyle, ExternalAgentConfig, AssistantAgentConfig
from ibm_watsonx_orchestrate.agent_builder.tools import tool
import rich

@tool(name="testing_tool", description="testing tool")
def sample_tool():
    print("Hello")

calculus_knowledge_base = KnowledgeBase(
    name="calculus_knowledge_base",
    description="Knowledge base with documentation about how to do calculus",
    conversational_search_tool=ConversationalSearchConfig(
        index_config=[
            IndexConnection(milvus=MilvusConnection(
                grpc_host="https://xxxx.lakehouse.appdomain.cloud",
                database="default",
                collection="calculus_docs",
                index="dense",
                embedding_model_id="sentence-transformers/all-minilm-l12-v2",
                field_mapping=FieldMapping(title="title", body="text")
            ))
        ]
    )
)

agent2 = ExternalAgent(
    name="news_agent",
    title="News Agent",
    description="An agent running in a custom langchain container capable of communicating with multiple news sources to combat disinformation.",
    tags=[
        "test",
        "other"
    ],
    api_url="http://my-codeengine.cloud.ibm.com/chat/completions",
    chat_params={
        "stream": True
    },
    config=ExternalAgentConfig(
        hidden=False,
        enable_co=False
    ),
    nickname="news_agent",
    app_id="my_news_agent"
)

agent1 = Agent(
    name="math_agent",
    description="""
        You are a helpful calculation agent that assists the user in performing math. 
        This includes performing mathematical operations and providing practical use cases for math in everyday life.
  
        Always solve the mathematical equations using the correct order of operations (PEMDAS):
            Parentheses
            Exponents (including roots, powers, etc.)
            Multiplication and Division (from left to right)
            Addition and Subtraction (from left to right)
  
        Make sure to include decimal points when the user's input includes a float.
    """,
    llm="watsonx/ibm/granite-3-8b-instruct", #Optional, Default=watsonx/meta-llama/llama-3-1-70b-instruct
    style=AgentStyle.REACT,  #Optional, Valid options = [AgentStyle.DEFAULT, AgentStyle.REACT]
    collaborators=[
        agent2,
        "algebra_agent"
    ],
    # collaborators can take a mix of Agent objects or string with agent names
    tools=[
        "add",
        "subtract",
        sample_tool,
    ],
    # tools can take a mix of Tool objects or string with tool names
    knowledge_base=[
        "algebra_knowledge_base",
        calculus_knowledge_base
    ]
    # knowledge_base can take a mix of KnowledgeBase objects or string with knowledge_base names
)

agent5 = AssistantAgent(
    name="hr_agent",
    title="HR Agent",
    description="""
        An assistant for answering general HR queries
    """,
    tags=[
        "hr",
        "wxa"
    ],
    nickname="hr_agent",
    config=AssistantAgentConfig(
        api_version="2021-11-27",
        assistant_id="27de49b4-4abc-4c1a-91d7-1a612c36fd18",
        crn="crn:v1:aws:public:wxo:us-east-1:sub/20240412-0950-3314-301c-8dfc5950d337:20240415-0552-2619-5017-c41d62e59413::",
        instance_url="https://api.us-east-1.aws.watsonassistant.ibm.com/instances/20240415-0552-2619-5017-c41d62e59413",
        environment_id="ef8b93b2-4a4c-4eb8-b479-3fc056c4aa4f"
    ),
    app_id="my_hr_agent"
)
rich.print(agent5.dumps_spec())