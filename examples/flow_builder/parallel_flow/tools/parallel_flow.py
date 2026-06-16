"""
A sample workflow that implements a simple feature delivery process with multiple phases:
- Phase 1: Design and Architecture (done in parallel). Design may or may not be needed. 
  Architecture may or may not be needed. If neither are needed, this phase simply exits.
- Phase 2: Development (starts after Design and Architecture are done). Multiple squads working in parallel.
- Phase 3: QA (starts after Development is done)

General structure of the workflow is:
  Start > Phase 1 (parallel) > Phase 2 (parallel) > Phase 3 (QA) > End
"""

from typing import List
from pydantic import BaseModel, Field
from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, ScriptNode, START, END
)

class FlowInput(BaseModel):
    """Input schema for the feature delivery workflow"""
    feature_name: str = Field(description="Name of the feature to deliver")
    design_needed: bool = Field(default=True, description="Whether design work is needed")
    arch_needed: bool = Field(default=True, description="Whether architecture work is needed")

class FlowOutput(BaseModel):
    """Output schema for the feature delivery workflow"""
    status: str = Field(description="Final status of the feature delivery")
    phases_completed: List[str] = Field(description="List of completed phases")

class PrivateState(BaseModel):
    """Private state to track workflow progress"""
    design_needed: bool = Field(default=False, description="Whether design is needed")
    arch_needed: bool = Field(default=False, description="Whether architecture is needed")
    phases_completed: List[str] = Field(default_factory=list, description="Completed phases")

@flow(
    name="feature_delivery_workflow",
    display_name="Feature Delivery Workflow",
    description="A workflow demonstrating parallel execution in multiple phases",
    input_schema=FlowInput,
    output_schema=FlowOutput,
    private_schema=PrivateState
)
def build_feature_delivery_flow(aflow: Flow) -> Flow:
    """
    Build a feature delivery workflow with three phases:
    1. Phase 1: Design and Architecture (conditional parallel execution)
    2. Phase 2: Development (unconditional parallel execution by 3 squads)
    3. Phase 3: QA (sequential)
    """
    
    # Initialize private state from input
    init_state: ScriptNode = aflow.script(
        name="init_state",
        script="""
flow.private.design_needed = flow.input.design_needed
flow.private.arch_needed = flow.input.arch_needed
flow.private.phases_completed = []
        """
    )
    
    # ============================================================================
    # PHASE 1: Design and Architecture (Conditional Parallel)
    # ============================================================================
    # This phase uses parallel_conditions to conditionally execute design and/or
    # architecture work based on the input flags. If neither is needed, it skips
    # directly to the next phase.
    
    phase1_parallel = aflow.parallel_conditions(
        name="parallel_phase1",
        display_name="Phase 1 - Design & Architecture"
    )
    
    # Design work (only if needed) - create in the parallel subflow
    design_work: ScriptNode = phase1_parallel.script(
        name="design_work",
        display_name="Design Work",
        script="""
# Simulate design work
print("Starting design work...")
time.sleep(0.1)
flow.private.phases_completed.append("Design")
print("Design work completed")
        """
    )
    
    # Architecture work (only if needed) - create in the parallel subflow
    architecture_work: ScriptNode = phase1_parallel.script(
        name="architecture_work",
        display_name="Architecture Work",
        script="""
# Simulate architecture work
print("Starting architecture work...")
time.sleep(0.1)
flow.private.phases_completed.append("Architecture")
print("Architecture work completed")
        """
    )
    
    # Placeholder for when neither design nor architecture is needed - create in the parallel subflow
    phase1_skip: ScriptNode = phase1_parallel.script(
        name="phase1_skip",
        display_name="Phase 1 Skip",
        script="""
print("Phase 1: No design or architecture work needed, skipping...")
        """
    )
    
    # Add conditional branches to phase 1 parallel
    # The condition() method automatically creates edges from START to each node
    phase1_parallel.condition(
        expression="flow.private.design_needed is True",
        to_node=design_work
    ).condition(
        expression="flow.private.arch_needed is True",
        to_node=architecture_work
    ).condition(
        default=True,
        to_node=phase1_skip
    )
    
    # Connect each node to END within the parallel subflow
    phase1_parallel.sequence(design_work, END)
    phase1_parallel.sequence(architecture_work, END)
    phase1_parallel.sequence(phase1_skip, END)

    
    # ============================================================================
    # PHASE 2: Development (Unconditional Parallel)
    # ============================================================================
    # This phase uses parallel to execute work by 3 squads in parallel.
    # All squads always execute (no conditions), demonstrating unconditional
    # parallel execution.
    
    phase2_parallel = aflow.parallel(
        evaluator=None,  # No evaluator means all paths execute
        name="parallel_phase2",
        display_name="Phase 2 - Development"
    )
    
    # Squad 1 work
    squad1_work: ScriptNode = phase2_parallel.script(
        name="squad1_work",
        display_name="Squad 1 Development",
        script="""
# Simulate squad 1 development work
print("Squad 1: Starting development...")
time.sleep(0.1)
print("Squad 1: Development completed")
        """
    )
    
    # Squad 2 work
    squad2_work: ScriptNode = phase2_parallel.script(
        name="squad2_work",
        display_name="Squad 2 Development",
        script="""
# Simulate squad 2 development work
print("Squad 2: Starting development...")
time.sleep(0.1)
print("Squad 2: Development completed")
        """
    )
    
    # Squad 3 work
    squad3_work: ScriptNode = phase2_parallel.script(
        name="squad3_work",
        display_name="Squad 3 Development",
        script="""
# Simulate squad 3 development work
print("Squad 3: Starting development...")
time.sleep(0.1)
print("Squad 3: Development completed")
        """
    )
    
    # Track phase 2 completion
    phase2_complete: ScriptNode = aflow.script(
        name="phase2_complete",
        display_name="Phase 2 Complete",
        script="""
flow.private.phases_completed.append("Development (Squad 1)")
flow.private.phases_completed.append("Development (Squad 2)")
flow.private.phases_completed.append("Development (Squad 3)")
print("Phase 2: All squads completed development")
        """
    )
    
    # Connect phase 2 internal nodes
    phase2_parallel.sequence(START, squad1_work, END)
    phase2_parallel.sequence(START, squad2_work, END)
    phase2_parallel.sequence(START, squad3_work, END)
    
    # ============================================================================
    # PHASE 3: QA (Sequential)
    # ============================================================================
    
    qa_work: ScriptNode = aflow.script(
        name="qa_work",
        display_name="Phase 3 - QA",
        script="""
# Simulate QA work
print("Starting QA testing...")
time.sleep(0.1)
flow.private.phases_completed.append("QA")
print("QA testing completed")
        """
    )
    
    # Final output mapping
    finalize: ScriptNode = aflow.script(
        name="finalize",
        display_name="Finalize Workflow",
        script="""
flow.output.status = "Feature delivery completed successfully"
flow.output.phases_completed = flow.private.phases_completed
print(f"Workflow completed. Phases: {flow.private.phases_completed}")
        """
    )
    
    # ============================================================================
    # WORKFLOW SEQUENCE
    # ============================================================================
    # Connect all phases in sequence:
    # Start > Init > Phase1 (parallel) > Phase2 (parallel) > Phase3 (QA) > Finalize > End
    
    aflow.edge(START, init_state)
    aflow.edge(init_state, phase1_parallel)
    
    aflow.edge(phase1_parallel, phase2_parallel)
    
    # Connect phase 2 to completion tracker
    aflow.edge(phase2_parallel, phase2_complete)
    
    # Connect to phase 3 and finalize
    aflow.edge(phase2_complete, qa_work)
    aflow.edge(qa_work, finalize)
    aflow.edge(finalize, END)
    
    return aflow

# Made with Bob
