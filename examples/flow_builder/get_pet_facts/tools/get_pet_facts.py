"""
Based on the request, we will return the list of facts about the pet.
A pet can be either a cat or a dog.
"""

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import (
    Flow, flow, START, END, Branch
)

class Pet(BaseModel):
    kind: str = Field(description="the kind of pet: dog or cat")

class PetFacts(BaseModel):
    facts: list[str] = Field(description="A list of facts about the pet")

@flow(
        name = "get_pet_facts",
        input_schema = Pet,
        output_schema = PetFacts
)
def build_get_pet_facts_flow(aflow: Flow) -> Flow:
    """ Based on the request, we will return the list of facts about the pet. A pet can be either a cat or a dog. """
    
    dog_fact_node = aflow.tool("getDogFact")
    cat_fact_node = aflow.tool("getCatFact")

    # create a branch
    check_pet_kind_branch: Branch = aflow.branch(evaluator="flow.input.kind.strip().lower() == 'dog'")
    aflow.edge(START, check_pet_kind_branch)

    # edges are automatically added when cases are added
    check_pet_kind_branch.case(True, dog_fact_node).case(False, cat_fact_node)

    aflow.edge(dog_fact_node, END)
    aflow.edge(cat_fact_node, END)

    return aflow
