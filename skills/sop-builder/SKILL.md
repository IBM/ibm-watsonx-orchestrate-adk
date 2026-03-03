---
name: sop-builder
description: Expert guidance for building a Standard Operating Procedure (SOP) from a workflow diagram, Langflow JSON, n8n JSON, BPMN model or workflow description. Focuses on business problem, data requirements, and business logic in plain language.
---

# Standard Operating Procedure (SOP) Generation

## Purpose
This SOP defines the process for analyzing BPMN diagrams, Langflow JSON specifications, or n8n workflow descriptions and generating **SOPs** that describe the business problem, data requirements, and business logic in plain language—without technical BPMN, Langflow, or workflow automation terminology.

## Objective
Transform technical workflow diagrams into **SOP documentation** that:
- Can be understood by non-technical stakeholders
- Focuses on business problems and solutions
- Defines data requirements clearly
- Describes business logic and decision-making
- Serves as a bridge between business requirements and technical implementation
- Contains ONLY factual information from the source specification

## Documentation Principles
**IMPORTANT**: Generate specifications based ONLY on factual information present in the source workflow/diagram.

**Rules:**
- Include ONLY what is explicitly defined or directly observable in the source
- Do NOT add speculative content about performance, timing, or optimization
- Do NOT include assumptions about non-functional characteristics unless explicitly specified
- Do NOT add arbitrary concerns, compliance requirements, or improvement suggestions
- Do NOT estimate durations, volumes, KPIs, or SLAs unless they are defined in the source
- Focus on WHAT the process does, not HOW WELL it might perform
- State when elements are "Not explicitly defined" rather than making assumptions

**Exception - Technical Dependencies:**
- DO document any APIs, MCP servers, security protocols, storage systems, databases, or other technical dependencies that are explicitly referenced in the specification
- Include specific details about these dependencies as stated in the source (e.g., API endpoints, authentication methods, database types, storage locations, MCP server configurations)
- Document integration requirements and technical constraints that are specified in the source

---

## Scope
This procedure applies to:
- BPMN diagrams (XML or visual)
- Langflow JSON specifications (exported flows)
- n8n workflows
- Other workflow automation specifications
- Business process descriptions

The output is an **SOP** written in natural language for business stakeholders.

### Langflow JSON Structure
When analyzing Langflow JSON files, extract information from:
- **Flow metadata**: Name, description, and overall purpose
- **Nodes**: Individual components representing process steps
  - `ChatInput`: Entry points for user input
  - `ChatOutput`: Exit points for results
  - Custom components: Business logic implementations
  - LLM components: AI-powered decision making
  - Data processing components: Transformations and validations
- **Edges**: Connections between nodes showing process flow
- **Global variables**: Configuration and dynamic values
- **Component templates**: Detailed configuration of each node including:
  - Input/output specifications
  - Field configurations
  - Validation rules
  - Business logic embedded in code fields

---

## Procedure

You are a business analyst specializing in translating technical workflows into clear business procedures. When provided with a workflow source (BPMN, n8n, or description), generate an **SOP** following this structure.

### 1. Executive Summary

Provide a concise overview for executives and decision-makers:

- **Procedure Name**: Clear, business-friendly name
- **Business Problem**: What problem does this procedure solve?
- **Business Objective**: What business outcome does this achieve?
- **Scope**: What is included and excluded
- **Key Benefits**: Top 3-5 business benefits
- **Stakeholders**: Who is involved or affected
- **Success Criteria**: How do we know this procedure is working?

### 2. Business Process Flow Diagram

Create a Mermaid flowchart diagram that visualizes the business process flow:

**Requirements**:
- Use Mermaid flowchart syntax (```mermaid flowchart TD```)
- Show all major process steps as rectangles
- Show decision points as diamonds
- Show start and end points clearly
- Use arrows to show flow direction
- Include conditional branching where applicable
- Use color coding to highlight different types of activities:
  - Start/End points (green/red)
  - Decision points (yellow)
  - Key business activities (blue for critical steps)
  - Standard process steps (white/default)
- Keep labels concise but descriptive
- Show loops for iterative processes

**Include a Legend** explaining:
- What each shape represents
- What colors indicate
- Key flow characteristics (sequential, parallel, conditional, etc.)
- Any special notations used

**Example Structure**:
```mermaid
flowchart TD
    Start([Start Event]) --> Step1[Process Step]
    Step1 --> Decision{Decision Point?}
    Decision -->|Yes| Step2[Action A]
    Decision -->|No| Step3[Action B]
    Step2 --> End([End])
    Step3 --> End
```

### 3. Business Context

#### 3.1 Problem Statement
Describe the business problem in detail:
- What challenge or inefficiency exists today?
- What is the impact of not solving this problem?
- Who is affected by this problem?
- What triggers the need for this procedure?

#### 3.2 Current State (If Applicable)
- How is this process handled today?
- What are the pain points?
- What manual steps exist?
- What inefficiencies or risks are present?

#### 3.3 Desired Future State
- What will change with this procedure?
- What improvements will be realized?
- What new capabilities will be enabled?

### 4. Procedure Overview

#### 4.1 Purpose and Scope
- **Primary Purpose**: What this procedure accomplishes
- **Secondary Purposes**: Additional benefits or outcomes
- **In Scope**: What activities are included
- **Out of Scope**: What is explicitly not included
- **Dependencies**: What must exist or happen first

#### 4.2 Roles and Responsibilities
For each role involved:
- **Role Name**: (e.g., Sales Representative, Customer Service Agent)
- **Responsibilities**: What they do in this procedure
- **Decision Authority**: What decisions they can make
- **Escalation Path**: When and to whom they escalate

#### 4.3 Frequency and Timing
- **Trigger**: What initiates this procedure
- **Frequency**: How often it runs (daily, on-demand, etc.)
- **Duration**: Expected time to complete
- **Business Hours**: When this procedure operates
- **Urgency**: Priority level and time sensitivity

### 5. Data Requirements

#### 5.1 Input Data
For each data element needed to start the procedure:

**Data Element Name**:
- **Description**: What this data represents
- **Source**: Where it comes from
- **Format**: How it's structured (in business terms)
- **Required/Optional**: Is it mandatory?
- **Validation Rules**: What makes it valid?
- **Example**: Sample data for clarity

Example:
```
Customer Order Information:
- Description: Details about what the customer wants to purchase
- Source: Customer via website, phone, or email
- Format: Order form with customer details, items, quantities, and delivery address
- Required: Yes
- Validation Rules: Must include valid customer contact, at least one item, and delivery address
- Example: John Smith orders 2 widgets to be delivered to 123 Main St
```

#### 5.2 Data Used During Procedure
Document data that is accessed or checked:

**Data Element Name**:
- **Description**: What this data represents
- **Purpose**: Why we need it
- **Source System**: Where it's stored
- **Access Frequency**: How often it's checked
- **Update Frequency**: How often it changes

#### 5.3 Output Data
For each data element produced:

**Data Element Name**:
- **Description**: What this data represents
- **Purpose**: How it will be used
- **Destination**: Where it goes
- **Format**: How it's structured
- **Retention**: How long it's kept

### 6. Custom Logic Documentation

If the specification contains custom logic implemented in programming languages (JavaScript, Java, Python, etc.), document this logic in pseudo Python code format for clarity and consistency.

**For each custom logic block:**

**Logic [Number]: [Logic Name/Purpose]**
- **Original Language**: The programming language used in the source
- **Purpose**: What this logic accomplishes in business terms
- **Inputs**: What data/variables are used
- **Outputs**: What is produced or returned
- **Pseudo Python Code**: Simplified Python-like representation of the logic

**Guidelines for Pseudo Python Code:**
- Use clear, readable Python syntax
- Add comments to explain business logic
- Simplify complex operations while preserving intent
- Use descriptive variable names
- Include error handling if present in original
- Show conditional logic clearly
- Document any external function calls or API interactions

**Example:**
```
Logic 1: Calculate Order Discount
- Original Language: JavaScript
- Purpose: Determine the discount percentage based on order total and customer loyalty tier
- Inputs: order_total (number), customer_tier (string)
- Outputs: discount_percentage (number)
- Pseudo Python Code:
```python
def calculate_order_discount(order_total, customer_tier):
    """
    Calculate discount based on order value and customer loyalty tier.
    Business Rule: Higher tiers get better discounts, larger orders get additional discounts.
    """
    # Base discount by customer tier
    if customer_tier == "platinum":
        base_discount = 0.15  # 15% for platinum customers
    elif customer_tier == "gold":
        base_discount = 0.10  # 10% for gold customers
    elif customer_tier == "silver":
        base_discount = 0.05  # 5% for silver customers
    else:
        base_discount = 0.0   # No discount for regular customers
    
    # Additional discount for large orders
    if order_total > 1000:
        volume_discount = 0.05  # Extra 5% for orders over $1000
    elif order_total > 500:
        volume_discount = 0.02  # Extra 2% for orders over $500
    else:
        volume_discount = 0.0
    
    # Calculate total discount (capped at 25%)
    total_discount = min(base_discount + volume_discount, 0.25)
    
    return total_discount
```
```


### 6.1 LLM Prompts Documentation

If the specification contains LLM system prompts or user prompts, document them in this section.

**For each LLM prompt:**

**Prompt [Number]: [Prompt Name/Purpose]**
- **Prompt Type**: System Prompt or User Prompt
- **Purpose**: What this prompt accomplishes in business terms
- **Context**: When and where this prompt is used in the process
- **Prompt Content**: The actual prompt text (preserve formatting and structure)
- **Expected Output**: What type of response or behavior is expected
- **Variables/Placeholders**: Any dynamic elements that get substituted

**Example:**
```
Prompt 1: Customer Service Response Generator
- Prompt Type: System Prompt
- Purpose: Guide the AI to generate professional, empathetic customer service responses
- Context: Used when responding to customer inquiries or complaints
- Prompt Content:
  """
  You are a professional customer service representative for [Company Name].
  Your role is to:
  - Respond with empathy and understanding
  - Provide clear, actionable solutions
  - Maintain a friendly but professional tone
  - Escalate complex issues when appropriate
  
  Customer Context: {customer_tier}, {previous_interactions}
  Issue Type: {issue_category}
  """
- Expected Output: A customer service response that addresses the issue while maintaining brand voice
- Variables/Placeholders:
  - {customer_tier}: Customer loyalty level (bronze/silver/gold/platinum)
  - {previous_interactions}: Number of previous support tickets
  - {issue_category}: Type of issue (billing, technical, general inquiry)
```

**Note**: Only include this section if LLM prompts exist in the source specification. If no prompts are present, omit this section entirely.

### 7. Business Procedure Steps

Write the procedure as a numbered list of business steps (not technical tasks). Use clear, action-oriented language.

**Format for each step:**

**Step [Number]: [Action Name]**
- **What Happens**: Describe the business activity in plain language
- **Who Does It**: Role responsible (or "System" if automated)
- **Why**: Business reason for this step
- **Inputs**: What information is needed
- **Outputs**: What is produced or updated
- **Duration**: Typical time required
- **Success Criteria**: How to know it's done correctly

**Example:**
```
Step 1: Verify Customer Order
- What Happens: Review the customer's order to ensure all required information is complete and accurate
- Who Does It: Order Processing Team (or System if automated)
- Why: Prevent processing incomplete or incorrect orders that would cause delays or errors
- Inputs: Customer order form with items, quantities, delivery address, and payment method
- Outputs: Validated order marked as "Ready for Processing" or "Needs Correction"
- Duration: 2-5 minutes
- Success Criteria: All required fields are complete, address is valid, items are available in catalog
```

### 8. Decision Points

For each decision in the procedure:

**Decision [Number]: [Decision Name]**
- **Question Being Answered**: What needs to be decided?
- **Who Decides**: Role or system making the decision
- **Decision Criteria**: What factors are considered?
- **Possible Outcomes**: What are the options?
- **Business Rules**: Rules that govern this decision
- **Impact**: What happens based on each outcome?

**Example:**
```
Decision 1: Is Inventory Available?
- Question Being Answered: Do we have enough stock to fulfill this order?
- Who Decides: Inventory Management System
- Decision Criteria: Current stock levels vs. order quantity for each item
- Possible Outcomes:
  * Yes - All items in stock → Proceed to payment
  * No - One or more items out of stock → Cancel order and notify customer
- Business Rules:
  * Must have 100% of items available (no partial fulfillment)
  * Stock check must be real-time to prevent overselling
- Impact:
  * If Yes: Customer gets their order, revenue is captured
  * If No: Customer is disappointed but informed, no false promises
```

### 9. Business Rules

Document all business rules that govern this procedure:

**Rule [Number]: [Rule Name]**
- **Rule Statement**: Clear statement of the rule
- **Business Rationale**: Why this rule exists
- **Applies To**: What situations or steps
- **Enforced By**: Who or what enforces it
- **Exceptions**: When this rule doesn't apply
- **Consequences**: What happens if violated

**Example:**
```
Rule 1: Payment Before Shipment
- Rule Statement: No order shall be shipped until payment is successfully processed and confirmed
- Business Rationale: Protect company revenue and minimize financial risk from unpaid orders
- Applies To: All customer orders regardless of size or customer type
- Enforced By: Order Management System (automated control)
- Exceptions: Pre-approved corporate accounts with net-30 terms
- Consequences: If violated, company loses revenue and incurs shipping costs for unpaid orders
```

### 10. Exception Handling

Document what happens when things go wrong:

**Exception [Number]: [Exception Name]**
- **What Goes Wrong**: Description of the problem
- **How It's Detected**: How we know there's a problem
- **Business Impact**: What's at risk
- **Response Procedure**: What we do about it
- **Responsible Party**: Who handles it
- **Prevention**: How to avoid this in the future
- **Escalation**: When to escalate and to whom

### 10. Integration Points

Describe interactions with other systems or procedures (in business terms):

**Integration [Number]: [System/Procedure Name]**
- **Purpose**: Why we interact with this system
- **What We Send**: Information provided to the system
- **What We Receive**: Information received back
- **Timing**: When this interaction happens
- **Dependency**: What happens if this system is unavailable
- **Business Owner**: Who owns the other system/procedure

### 11. Notes and Observations

#### 11.1 Process Characteristics
Document observable characteristics from the source specification:
- Process complexity (simple, moderate, complex)
- Automation level (manual, semi-automated, fully automated)
- Integration requirements (systems involved)
- Data volume characteristics (if specified)

#### 11.2 Limitations and Constraints
Document only what is explicitly stated or observable:
- Known limitations in the current design
- Explicit constraints mentioned in the specification
- Dependencies that must be satisfied
- Scope boundaries

#### 11.3 Additional Context
Include only if explicitly provided in the source:
- Regulatory requirements (if specified)
- Compliance needs (if specified)
- Quality standards (if specified)
- Performance targets (if specified)

**Note**: If any of these elements are not defined in the source specification, state "Not explicitly defined in source specification" rather than making assumptions.

---

## Writing Guidelines

### Language and Style
- **Use Business Language**: Avoid technical jargon, BPMN terms, or automation terminology
- **Be Specific**: Use concrete examples and scenarios
- **Be Action-Oriented**: Focus on what happens and why, not how it's implemented
- **Be Clear**: Write for someone unfamiliar with the process
- **Be Concise**: Eliminate unnecessary words while maintaining clarity

### Terminology to Avoid
❌ **Don't Use**: BPMN, nodes, gateways, sequence flows, service tasks, message events, XML, JSON, Langflow components, edges, ChatInput, ChatOutput, API calls, webhooks, HTTP requests, database queries, global variables, component templates

✅ **Do Use**: Steps, decisions, activities, information, data, systems, checks, notifications, updates, records, forms, reports, inputs, outputs, configuration values

### Examples of Translation

**BPMN Technical**: "The exclusive gateway evaluates the inventory_available boolean attribute"
**Business**: "We check whether we have enough stock to fulfill the order"

**BPMN Technical**: "A service task calls the payment API endpoint with order data"
**Business**: "We process the customer's payment through our payment system"

**BPMN Technical**: "The subprocess contains embedded error boundary events"
**Business**: "If something goes wrong during this step, we have procedures to handle the problem"

**Langflow Technical**: "The ChatInput node receives user message and passes it to the ActionItemExtractor component"
**Business**: "The system receives the user's request and analyzes it to identify action items"

**Langflow Technical**: "The component template defines input_types as ['Message', 'Data', 'Text']"
**Business**: "The system accepts information in various formats including messages and structured data"

**Langflow Technical**: "The edge connects node A's output handle to node B's input handle"
**Business**: "Information flows from step A to step B"

**Langflow Technical**: "Global variable 'api_key' is configured with type 'str' and marked as required"
**Business**: "The system requires authentication credentials to access external services"

### Formatting Standards
- Use clear headings and subheadings
- Use bullet points for lists
- Use numbered lists for sequential steps
- Use tables for structured comparisons
- Use examples to illustrate complex concepts
- Use bold for emphasis on key terms
- Use quotes for specific data values or examples

---

## Quality Standards

### Completeness
- All sections must be addressed
- Sections without source information should state "Not explicitly defined in source specification"
- All decisions must have clear criteria from the source
- All data elements must be defined based on source information

### Accuracy
- Information must match the source workflow exactly
- No hallucination or invention of details
- Do NOT make assumptions - only document what is observable
- If information is inferred, clearly state "Inferred from [specific source element]"
- If information is missing, state "Not explicitly defined in source specification"

### Clarity
- Readable by non-technical business stakeholders
- Free of technical jargon
- Concrete examples provided where available in source
- Logical flow and organization

### Business Focus
- Emphasizes business value and outcomes observable in the workflow
- Explains "why" based on what can be deduced from the source
- Connects to business objectives only when evident in the source
- Addresses stakeholder concerns only when specified in the source

---

## Output Format

### File Naming Convention
`[procedure-name]-sop.md`

Example: `order-fulfillment-sop.md`

### Document Header
```markdown
# [Procedure Name] - SOP

**Document Type**: SOP
**Version**: 1.0
**Date**: [Date]
**Author**: [Name]
**Source**: [Original workflow file/diagram]
**Status**: [Draft/Review/Approved]

---

## Document Control

**Approvers**:
- Business Owner: [Name/TBD]
- Process Owner: [Name/TBD]
- Compliance: [Name/TBD]

**Review Cycle**: [Frequency]
**Next Review Date**: [Date]

---
```

### Document Structure
Follow the sections outlined above in order:
1. Executive Summary
2. Business Process Flow Diagram
3. Business Context
4. Procedure Overview
5. Data Requirements
6. Custom Logic Documentation (if applicable)
6.1. LLM Prompts Documentation (if applicable)
7. Business Procedure Steps
8. Decision Points
9. Business Rules
10. Exception Handling
11. Integration Points
12. Notes and Observations

---

## Usage Instructions

### To Use This SOP:

1. **Provide the Source**: Share the BPMN diagram, Langflow JSON file, n8n workflow, or process description
2. **Specify Context**: Provide any additional business context or constraints
3. **Review Output**: Verify the business specification for accuracy
4. **Iterate**: Request clarifications or additional details as needed
5. **Validate**: Have business stakeholders review and approve
6. **Maintain**: Update as the procedure evolves

### Example Request (BPMN):

```
Please analyze the following workflow and generate an SOP:

@order-fulfillment-process.bpmn

Additional context:
- This is for an e-commerce company
- Average order value is $150
- Processing 500-1000 orders per day
- Customer service team has 10 people
- Focus on customer experience and efficiency
```

### Example Request (Langflow):

```
Please analyze the following Langflow workflow and generate an SOP:

@action-item-extractor.json

Additional context:
- This is for a project management team
- Processes meeting transcripts and chat logs
- Extracts actionable tasks with assignees and due dates
- Used by 50+ team members
- Focus on task tracking and accountability
```

---

## Provide Your Workflow Below:

**Workflow Source**:
```
@your-workflow-file  # Replace with your BPMN, Langflow JSON, n8n, or workflow file
```

**Additional Context** (optional but recommended):
```
- Industry/business type:
- Scale/volume:
- Key stakeholders:
- Primary objectives:
- Known constraints:
- Specific concerns:
```

---

## Workflow-Specific Extraction Guidelines

### Langflow JSON Files

When analyzing Langflow JSON files, follow these additional guidelines:

### 1. Identify Process Flow from Edges
- Map `edges` array to understand the sequence of operations
- `source` and `target` fields indicate flow direction
- Multiple edges from one node indicate branching/decision points
- Edges returning to previous nodes indicate loops

### 2. Extract Business Logic from Nodes
For each node in the `nodes` array:
- **Node ID**: Used for tracking but translate to business step names
- **Node Type**: Indicates the component type (ChatInput, ChatOutput, custom components)
- **Display Name**: Often contains business-friendly names
- **Description**: May contain business purpose
- **Template Fields**: Configuration that reveals business rules and logic
- **Code Fields**: May contain embedded business logic (translate to pseudo-code)

### 3. Understand Data Flow
- **Input/Output Types**: Reveal what data moves between steps
- **Field Configurations**: Show validation rules and data requirements
- **Global Variables**: Indicate external dependencies and configuration needs

### 4. Identify Decision Points
Look for:
- Conditional components
- Multiple outgoing edges from a single node
- Components with boolean outputs
- Branching logic in custom code

### 5. Extract Business Rules
From:
- Validation rules in field configurations
- Conditional logic in custom components
- Required vs optional field settings
- Data type constraints

### 6. Document Integration Points
Identify from:
- API call components
- Database query components
- External service integrations
- Global variables pointing to external systems

### n8n Workflows

When analyzing n8n workflow JSON files, follow these additional guidelines:

#### 1. Identify Process Flow from Connections
- Map `connections` object to understand the sequence of operations
- Each node's connections show which nodes receive its output
- Multiple connections from one node indicate branching/decision points
- Connections returning to previous nodes indicate loops

#### 2. Extract Business Logic from Nodes
For each node in the `nodes` array:
- **Node Name**: Translate to business step names
- **Node Type**: Indicates the operation type (HTTP Request, IF, Set, etc.)
- **Parameters**: Configuration that reveals business rules and logic
- **Notes**: May contain business purpose and context
- **Credentials**: Indicate external system integrations

#### 3. Understand Data Flow
- **Node Outputs**: Reveal what data moves between steps
- **Expressions**: Show data transformations and calculations
- **Parameters**: Show validation rules and data requirements

#### 4. Identify Decision Points
Look for:
- IF nodes for conditional logic
- Switch nodes for multi-way branching
- Filter nodes for data-based routing
- Multiple output connections from a single node

#### 5. Extract Business Rules
From:
- IF node conditions
- Filter node criteria
- Set node value mappings
- Function node logic (translate to pseudo-code)

#### 6. Document Integration Points
Identify from:
- HTTP Request nodes (API calls)
- Database nodes (queries and updates)
- Webhook nodes (external triggers)
- Credential configurations (external systems)

---