from ibm_watsonx_orchestrate.flow_builder.flows.flow import UserFlow
from typing import Optional
from ibm_watsonx_orchestrate.flow_builder.flows import AgentNode, EndNode, ScriptNode


from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END, Branch
)
from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.types import UserFieldKind

class FlowInput(BaseModel):
    original_issue: str = Field(description="Original Issue")

class FlowOutput(BaseModel):
    steps_taken: list[str] = Field(description="Steps Taken")
    final_solution: str = Field(description="Final Solution")

class AvailableAgent(BaseModel):
    agent: str = Field(description="Agent Name")
    description: str = Field(description="Agent Description")

class AvailableAgents(BaseModel):
    agents: list[AvailableAgent] = Field(description="Available Agents")

class SwarmState(BaseModel):
    original_issue: str
    steps_taken: list[str]
    final_solution: Optional[str] = Field(description="Final Solution (optional)", default=None)
    current_status: Optional[str] = Field(description="Current Status (optional)", default="pending")
    question: Optional[str] = Field(description="Question (optional)", default="")
    available_agents: AvailableAgents = Field(description="Available Agents")
    next_agent: str
    next_agent_instruction: str = Field(description="Next Agent Instruction")
    agents_called: list[str] = Field(description="Agents Called", default=[])
    iteration: int

class AgentInput(BaseModel):
    original_issue: str
    steps_taken: list[str]
    agent_instruction: str
    available_agents: AvailableAgents = Field(description="Available Agents")

class AgentOutput(BaseModel):
    steps_taken: Optional[list[str] | str] = Field(description="Steps Taken", default=[])
    final_solution: Optional[str] = Field(description="Final Solution", default=None)
    current_status: Optional[str] = Field(description="Current Status", default=None)
    question: Optional[str] = Field(description="Question (optional)", default=None)
    next_agent: Optional[str] = Field(description="Next Agent", default=None)
    next_agent_instruction: Optional[str] = Field(description="Next Agent Instruction", default=None)

@flow(
    name="triage_issue_flow",
    description="Flow to triage customer issue",
    input_schema=FlowInput,
    output_schema=FlowOutput,
    private_schema=SwarmState
)
def build_triage_issue_flow(flow: Flow) -> Flow:

    # setup the Swarm State
    setup_state: ScriptNode = flow.script(name="setup_swarm_state",
        script="""
flow.private.original_issue = flow.input.original_issue
flow.private.steps_taken = []
flow.private.final_solution = None
flow.private.next_agent = "triage_agent"
flow.private.next_agent_instruction = "Analyze the issue, classify it to either billing, technical or unknown (fallback) and route to the next agent."
flow.private.iteration = 0
flow.private.current_status = "Open"
flow.private.question = ""
flow.private.agents_called = []
flow.private.available_agents = [
    {
        "agent": "triage_agent",
        "description": "An agent that will route issue to the correct agents"
    },
    {
        "agent": "billing_agent",
        "description": "An agent that will solve billing issues"
    },
    {
        "agent": "technical_agent",
        "description": "An agent that will solve technical issues"
    },
    {
        "agent": "fallback_agent",
        "description": "An agent that handle any issues that are not handled by other agents"
    }
]
        """)

    triage_agent: AgentNode = flow.agent(
        name="triage_agent", 
        agent="triage_agent", 
        message="""
Follow <instruction> to process the <issue>{original_issue}</issue>:

1. You are the 'triage_agent'.
2. DO NOT generate conversational responses, greetings, or questions.
3. Analyze the issue and classify it as:
    - billing
    - technical
    - unknown (fallback)
Then route to the appropriate next agent.
4. Populate the following fields in the output:
    - steps_taken: list describing routing decisions (e.g., ["Analyzed user intent.", "Classified as Technical issue."])
    - next_agent: chosen agent from <available_agents>{available_agents}</available_agents>
    - next_agent_instruction: 1–2 sentences explaining why the next agent is receiving the context and what they should do
    (e.g., "Customer reports login failure after refund. Investigate authentication system.").
    - current_status: concise factual status message (e.g., "Routing to Technical Agent.")
    - final_solution: always set to "" (triage_agent does not solve issues).
5. If this agent is repeatedly called for the same issue (see <issue> and <agents_called>{flow.private.agents_called}</agents_called>):
    - Set next_agent to 'fallback_agent'.
6. Ensure the output strictly conforms to the JSON schema in <output_schema>{self.spec.output_schema}</output_schema>.
7. Use the provided <instruction>{agent_instruction}</instruction> for additional context.
8. Review <steps_taken>{flow.private.steps_taken}</steps_taken> for additional context.
9. Do not include any text outside the JSON object.

Constraints:
- Do not attempt to solve the issue or use external APIs.
- Do not include any text outside the JSON object.

Example Output (Routing to Billing Agent):
{
    "steps_taken": ["Analyzed user intent.", "Classified as Billing issue."],
    "final_solution": "",
    "current_status": "Routing to Billing Agent.",
    "next_agent": "billing_agent",
    "next_agent_instruction": "Customer reports double charge. Investigate transaction ID X and issue refund."
}

Example Output (Routing to Technical Agent):
{
    "steps_taken": ["Analyzed user intent.", "Classified as Technical issue."],
    "final_solution": "",
    "current_status": "Routing to Technical Agent.",
    "next_agent": "technical_agent",
    "next_agent_instruction": "Customer reports app crash during login. Diagnose and resolve authentication error."
}

Example Output (Routing to Fallback Agent):
{
    "steps_taken": ["Analyzed user intent.", "Unable to classify query after repeated attempts."],
    "final_solution": "solution not found",
    "current_status": "Workflow concluded as unclassifiable.",
    "next_agent": "fallback_agent",
    "next_agent_instruction": "System cannot proceed. No valid  "next_agent_instruction": "System cannot proceed. No valid classification possible."
}
            """,
        input_schema=AgentInput,
        output_schema=AgentOutput
        )
    
    update_state_from_triage: ScriptNode = flow.script(
        name="update_state_from_triage", 
        script="""
if flow.triage_agent.output.steps_taken is not None:
    if isinstance(flow.triage_agent.output.steps_taken, str):
        flow.private.steps_taken.append(flow.triage_agent.output.steps_taken)
    if isinstance(flow.triage_agent.output.steps_taken, list):
        flow.private.steps_taken.extend(flow.triage_agent.output.steps_taken)
flow.private.final_solution = flow.triage_agent.output.final_solution
flow.private.current_status = flow.triage_agent.output.current_status
flow.private.next_agent = flow.triage_agent.output.next_agent
flow.private.next_agent_instruction = flow.triage_agent.output.next_agent_instruction
flow.private.iteration += 1
flow.private.agents_called.append("triage_agent")
if flow.triage_agent.output.question:
    flow.private.question = flow.triage_agent.output.question
else:
    flow.private.question = ""
        """,
        )

    billing_agent: AgentNode = flow.agent(
        name="billing_agent", 
        agent="billing_agent", 
        message="""
Follow <instruction> to process the <issue>{original_issue}</issue>:

1. You are the 'billing_agent'.
2. DO NOT generate conversational responses, greetings.
3. Attempt to resolve the billing issue using provided tools.
4. Populate the following fields in the output:
    - steps_taken: list of actions performed (e.g., ["Checked payment status.", "Processed refund."])
    - final_solution:
        - If the issue is fully resolved: set to a concise, factual summary (e.g., "Refund of $50 processed for transaction ID X.")
        - If unresolved: set final_solution to "".
    - current_status: concise factual status message (e.g., "Subscription canceled." or "Unable to resolve billing issue.")
    - next_agent:
        - If resolved: set to 'billing_agent' (terminal state).
        - If unresolved and technical error detected: set to 'technical_agent'.
        - If unresolved after repeated attempts: set to 'fallback_agent'.
        - If resolved but new non-billing issue detected: set to 'triage_agent'.
    - next_agent_instruction: 1–2 sentences explaining why the next agent is receiving the context and what they should do
      (e.g., "Customer reports login failure after refund. Investigate technical issue.").
4.5 Only populate the 'question' field if the customer ID is not provided and cannot be found in the <steps_taken>.  Do not ask for any other question.
5. If this agent is repeatedly called for the same issue (see <issue> and <agents_called>{flow.private.agents_called}</agents_called>):
    - Set next_agent to 'fallback_agent'.
6. Ensure the output strictly conforms to the JSON schema in <output_schema>{self.spec.output_schema}</output_schema>.
7. Use the provided <instruction>{agent_instruction}</instruction> for additional context.
8. Review <steps_taken>{flow.private.steps_taken}</steps_taken> for additional context.
9. Do not include any text outside the JSON object.

Constraints:
- Do not attempt to solve non-billing issues.
- Do not include any text outside the JSON object.
- Always attempt resolution using provided tools before routing.

Example Output (Issue Resolved):
{
  "steps_taken": ["Checked payment status.", "Processed refund."],
  "final_solution": "Refund of $50 processed for transaction ID X.",
  "current_status": "Billing issue resolved.",
  "next_agent": "billing_agent",
  "next_agent_instruction": ""
}

Example Output (Routing to Technical Agent):
{
  "steps_taken": ["Attempted refund.", "Detected API error preventing transaction."],
  "final_solution": "",
  "current_status": "Routing to Technical Agent for troubleshooting.",
  "next_agent": "technical_agent",
  "next_agent_instruction": "Payment API server unresponsive. Diagnose and restore connectivity."
}

Example Output (Routing to Fallback Agent):
{
  "steps_taken": ["Attempted refund multiple times.", "Unable to resolve after repeated attempts."],
  "final_solution": "",
  "current_status": "Workflow concluded as unresolved billing failure.",
  "next_agent": "fallback_agent",
  "next_agent_instruction": "System cannot proceed. Billing issue unresolvable."
}

Example Output (when there is a question):
{
  "steps_taken": ["Attempted refund multiple times.", "Find customer ID."],
  "final_solution": "",
  "current_status": "Need to ask for customer ID.",
  "next_agent": "billing_agent",
  "next_agent_instruction": "System cannot proceed. Need customer ID.",
  "question": "What is the customer ID?"
}
""",
        input_schema=AgentInput,
        output_schema=AgentOutput
        )

    update_state_from_billing: ScriptNode = flow.script(
        name="update_state_from_billing", 
        script="""
if flow.billing_agent.output.steps_taken is not None:
    if isinstance(flow.billing_agent.output.steps_taken, str):
        flow.private.steps_taken.append(flow.billing_agent.output.steps_taken)
    if isinstance(flow.billing_agent.output.steps_taken, list):
        flow.private.steps_taken.extend(flow.billing_agent.output.steps_taken)
flow.private.final_solution = flow.billing_agent.output.final_solution
flow.private.current_status = flow.billing_agent.output.current_status
flow.private.next_agent = flow.billing_agent.output.next_agent
flow.private.next_agent_instruction = flow.billing_agent.output.next_agent_instruction
flow.private.iteration += 1
flow.private.agents_called.append("billing_agent")
if flow.billing_agent.output.question:
    flow.private.question = flow.billing_agent.output.question
else:
    flow.private.question = None
        """,
        )

    technical_agent: AgentNode = flow.agent(
        name="technical_agent", 
        agent="technical_agent", 
        message="""
Follow <instruction> to process the <issue>{original_issue}</issue>:

1. You are the 'technical_agent'.
2. DO NOT generate conversational responses, greetings, or questions.
3. Diagnose and attempt to resolve the technical issue using provided tools.
4. Populate the following fields in the output:
    - steps_taken: list of diagnostic actions performed (e.g., ["Ran system diagnostics.", "Cleared cache."])
    - final_solution:
        - If the issue is fully resolved: set to a concise, actionable resolution (e.g., "Issue fixed. Please clear browser cache and try logging in again.")
        - If unresolved: set final_solution to "".
    - current_status: concise factual status message (e.g., "Technical issue resolved." or "Unable to resolve after multiple attempts.")
    - next_agent:
        - If resolved: set to 'technical_agent' (terminal state).
        - If unresolved and related to payment/account: set to 'billing_agent'.
        - If unresolved and technical failure persists: set to 'fallback_agent'.
        - If partially resolved but next issue is non-technical: set to 'triage_agent'.
    - next_agent_instruction: 1–2 sentences explaining why the next agent is receiving the context and what they should do
      (e.g., "Customer account suspended due to billing error. Investigate payment status.").
5. If this agent is repeatedly called for the same issue (see <issue> and <agents_called>{flow.private.agents_called}</agents_called>):
    - Set next_agent to 'fallback_agent'.
6. Ensure the output strictly conforms to the JSON schema in <output_schema>{self.spec.output_schema}</output_schema>.
7. Use the provided <instruction>{agent_instruction}</instruction> for additional context.
8. Review <steps_taken>{flow.private.steps_taken}</steps_taken> for additional context.
9. Do not include any text outside the JSON object.

Constraints:
- Do not include any text outside the JSON object.
- Do not use external APIs beyond provided tools.
- Do not attempt financial transactions.

Example Output (Issue Resolved):
{
  "steps_taken": ["Ran system diagnostics.", "Cleared cache."],
  "final_solution": "Issue fixed. Please clear browser cache and try logging in again.",
  "current_status": "Technical issue resolved.",
  "next_agent": "technical_agent",
  "next_agent_instruction": ""
}

Example Output (Routing to Billing Agent):
{
  "steps_taken": ["Verified login failure.", "Detected account suspension due to billing."],
  "final_solution": "",
  "current_status": "Routing to Billing Agent for account reactivation.",
  "next_agent": "billing_agent",
  "next_agent_instruction": "Customer account suspended due to unpaid invoice. Investigate and resolve billing issue."
}

Example Output (Routing to Fallback Agent):
{
  "steps_taken": ["Ran diagnostics.", "Unable to resolve after multiple attempts."],
  "final_solution": "",
  "current_status": "Workflow concluded as unresolved technical failure.",
  "next_agent": "fallback_agent",
  "next_agent_instruction": "System cannot proceed. Technical issue unresolvable."
}
""",
        input_schema=AgentInput,
        output_schema=AgentOutput
        )

    update_state_from_technical: ScriptNode = flow.script(
        name="update_state_from_technical", 
        script="""
if flow.technical_agent.output.steps_taken is not None:
    if isinstance(flow.technical_agent.output.steps_taken, str):
        flow.private.steps_taken.append(flow.technical_agent.output.steps_taken)
    if isinstance(flow.technical_agent.output.steps_taken, list):
        flow.private.steps_taken.extend(flow.technical_agent.output.steps_taken)
flow.private.final_solution = flow.technical_agent.output.final_solution
flow.private.current_status = flow.technical_agent.output.current_status
flow.private.next_agent = flow.technical_agent.output.next_agent
flow.private.next_agent_instruction = flow.technical_agent.output.next_agent_instruction
flow.private.iteration += 1
flow.private.agents_called.append("technical_agent")
if flow.technical_agent.output.question:
    flow.private.question = flow.technical_agent.output.question
else:
    flow.private.question = ""
        """,
        )

    fallback_agent: AgentNode = flow.agent(
        name="fallback_agent", 
        agent="fallback_agent", 
        message="""
Follow <instruction> to process the <issue>{original_issue}</issue>:

1. You are the 'fallback_agent'.
2. DO NOT generate conversational responses, greetings, or questions.
3. Do not analyze or attempt to solve the original issue.
4. Populate the following fields in the output:
    - steps_taken: brief statement confirming inability to classify or resolve (e.g., ["Received unclassifiable query from Triage Agent."])
    - final_solution: literal string "solution not found"
    - current_status: concise factual status message (e.g., "Workflow concluded as unclassifiable.")
    - next_agent: set to 'fallback_agent' (indicates terminal workflow state)
    - next_agent_instruction: concluding statement (e.g., "System cannot proceed. No valid classification possible.")
5. Ensure the output strictly conforms to the JSON schema in <output_schema>{self.spec.output_schema}</output_schema>.
6. Use the provided <instruction>{agent_instruction}</instruction> for additional context.
7. Review <steps_taken>{flow.private.steps_taken}</steps_taken> for additional context.
8. Do not include any text outside the JSON object.

Constraints:
- Do not interpret or address the user's original query.
- Do not use external tools or APIs.
- Do not include any text outside the JSON object.

Example Output (Standard Fallback Response):
{
  "steps_taken": ["Received unclassifiable query from Triage Agent."],
  "final_solution": "solution not found",
  "current_status": "Workflow concluded as unclassifiable.",
  "next_agent": "fallback_agent",
  "next_agent_instruction": "System cannot proceed. No valid classification possible  "next_agent_instruction": "System cannot proceed. No valid classification possible."
}

        """,
        input_schema=AgentInput,
        output_schema=AgentOutput
        )

    update_state_from_fallback: ScriptNode = flow.script(
        name="update_state_from_fallback", 
        script="""
if flow.fallback_agent.output.steps_taken is not None:
    if isinstance(flow.fallback_agent.output.steps_taken, str):
        flow.private.steps_taken.append(flow.fallback_agent.output.steps_taken)
    if isinstance(flow.fallback_agent.output.steps_taken, list):
        flow.private.steps_taken.extend(flow.fallback_agent.output.steps_taken)
flow.private.final_solution = flow.fallback_agent.output.final_solution
flow.private.current_status = flow.fallback_agent.output.current_status
flow.private.next_agent = flow.fallback_agent.output.next_agent
flow.private.next_agent_instruction = flow.fallback_agent.output.next_agent_instruction
flow.private.iteration += 1
flow.private.agents_called.append("fallback_agent")
flow.private.question = ""
        """,
        )

    # ask questions that might be raised by the Agent
    ask_question_flow: UserFlow = flow.userflow(name="ask_question_flow")
    ask_question_node = ask_question_flow.field(direction="input", name="question", display_name="{flow.private.question}",  kind=UserFieldKind.Text)
    # because we are using a substituted string for display_name... which will be used as the question, we need to set the wrapper node display_name properly
    ask_question_node.spec.display_name = "question from agent"
    ask_question_flow.sequence(START, ask_question_node, END)

    update_state_from_question: ScriptNode = flow.script(
        name="update_state_from_question", 
        script="""
flow.private.steps_taken.append(f"question: {flow.private.question}, answer: {flow.ask_question_flow.output.value}")
flow.private.iteration += 1
flow.private.question = ""
        """,
        )

    last_update = flow.script(name="last_update", script="flow.private.final_solution = flow.private.final_solution")

    agent_router: Branch = flow.conditions()
    agent_router.condition(expression="flow.private.final_solution != None and len(flow.private.final_solution) > 0", to_node=last_update
        ).condition(expression="flow.private.iteration > 10", to_node=last_update
        ).condition(expression="flow.private.question != None and len(flow.private.question) > 0", to_node=ask_question_flow
        ).condition(expression="flow.private.next_agent != None and flow.private.next_agent == 'triage_agent'", to_node=triage_agent
        ).condition(expression="flow.private.next_agent != None and flow.private.next_agent == 'technical_agent'", to_node=technical_agent
        ).condition(expression="flow.private.next_agent != None and flow.private.next_agent == 'billing_agent'", to_node=billing_agent
        ).condition(expression="flow.private.next_agent != None and flow.private.next_agent == 'fallback_agent'", to_node=fallback_agent
        ).condition(default=True, to_node=last_update)

    flow.edge(START, setup_state)
    flow.edge(setup_state, agent_router)
    flow.edge(triage_agent, update_state_from_triage)
    flow.edge(update_state_from_triage, agent_router)

    flow.edge(billing_agent, update_state_from_billing)
    flow.edge(update_state_from_billing, agent_router)

    flow.edge(technical_agent, update_state_from_technical)
    flow.edge(update_state_from_technical, agent_router)

    flow.edge(fallback_agent, update_state_from_fallback)
    flow.edge(update_state_from_fallback, agent_router)

    flow.edge(ask_question_flow, update_state_from_question)
    flow.edge(update_state_from_question, agent_router)

    flow.edge(last_update, END)

    return flow
    