#!/bin/bash

# Activate SaaS environment
# orchestrate env activate PM_Agent_Builder_instance --apikey apiKeyHere

# Activate local environment
# orchestrate env activate local

# Import tools
orchestrate tools import -k python -f tools/calculate_violation_hours_simple.py
orchestrate tools import -k python -f tools/format_grievance_data_simple.py

# Import flow
orchestrate tools import -f tools/GrievanceExtractorFlow.json -k flow

# Import agent
orchestrate agents import -f agents/Doc_Processing_Agent_6873w7.yaml

# Made with Bob
