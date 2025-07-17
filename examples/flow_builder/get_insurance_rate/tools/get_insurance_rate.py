'''
Build a simple flow that will programmatically create a decisions table.
'''

from typing import Literal
from pydantic import BaseModel

from ibm_watsonx_orchestrate.flow_builder.flows import END, Flow, flow, START, DecisionsNode, DecisionsRule, DecisionsCondition

class Assessment(BaseModel):
    """
    This class represents the outcome of the assessment.
    """
    insurance_required: bool = False
    insurance_rate: float = 0.0
    assessment_error: str | None = None

class AssessmentData(BaseModel):
    """
    This class represents the data to be assessed.
    """
    loan_amount: float
    grade: Literal['A', 'B']

def build_decisions(aflow: Flow) -> DecisionsNode:
    """
    Build a Decisions Table programmatically as a node.

    e.g. read from an Excel spreadsheet or CSV and populate the decision table.
    """

    rules = []

    ## We will be build the rules programmatically.
    rule1 = DecisionsRule()
    rule1.condition("grade", DecisionsCondition().equal("A")).condition("loan_amount", DecisionsCondition().less_than(100000))
    rule1.action("insurance_required", False)
    rules.append(rule1)

    rule2 = DecisionsRule()
    rule2.condition("grade", DecisionsCondition().equal("A")).condition("loan_amount", DecisionsCondition().in_range(100000, 300000, True, False))
    rule2.action("insurance_required", True).action("insurance_rate", 0.001)
    rules.append(rule2)

    rule3 = DecisionsRule()
    rule3.condition("grade", DecisionsCondition().equal("A")).condition("loan_amount", DecisionsCondition().in_range(300000, 600000, True, False))
    rule3.action("insurance_required", True).action("insurance_rate", 0.003)
    rules.append(rule3)

    rule4 = DecisionsRule()
    rule4.condition("grade", DecisionsCondition().equal("A")).condition("loan_amount", DecisionsCondition().greater_than_or_equal(600000))
    rule4.action("insurance_required", True).action("insurance_rate", 0.005)
    rules.append(rule4)

    ## We will be build the rules programmatically.
    rule5 = DecisionsRule()
    rule5.condition("grade", DecisionsCondition().equal("B")).condition("loan_amount", DecisionsCondition().less_than(100000))
    rule5.action("insurance_required", False)
    rules.append(rule5)

    rule6 = DecisionsRule()
    rule6.condition("grade", DecisionsCondition().equal("B")).condition("loan_amount", DecisionsCondition().in_range(100000, 300000, True, False))
    rule6.action("insurance_required", True).action("insurance_rate", 0.0025)
    rules.append(rule6)

    rule7 = DecisionsRule()
    rule7.condition("grade", DecisionsCondition().equal("B")).condition("loan_amount", DecisionsCondition().in_range(300000, 600000, True, False))
    rule7.action("insurance_required", True).action("insurance_rate", 0.005)
    rules.append(rule7)

    rule8 = DecisionsRule()
    rule8.condition("grade", DecisionsCondition().equal("A")).condition("loan_amount", DecisionsCondition().greater_than_or_equal(600000))
    rule8.action("insurance_required", True).action("insurance_rate", 0.0075)
    rules.append(rule8)

    node = aflow.decisions(
        name="assess_insurance_rate",
        display_name="Assess insurance rate.",
        description="Based on credit rate and loan amount, assess insurance rate.",
        rules=rules,
        default_actions={
            "assessment_error": "Not assessed. Incorrect data submitted."
        },
        input_schema=AssessmentData,
        output_schema=Assessment
    )
    return node

@flow(
        name = "get_insurance_rate",
        input_schema=AssessmentData,
        output_schema=Assessment
    )
def build_get_insurance_rate(aflow: Flow = None) -> Flow:
    """
    Creates a flow to calculate the insurance rate based on provided information.
    """
    decisions_node = build_decisions(aflow)

    aflow.sequence(START, decisions_node, END)

    return aflow
