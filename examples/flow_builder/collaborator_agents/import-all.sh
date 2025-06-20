#!/usr/bin/env bash

orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )


for flow_tool in get_weather_data.py get_population_data.py aggregate_data.py get_city_founding_date.py; do
  orchestrate tools import -k python -f ${SCRIPT_DIR}/tools/${flow_tool}
done

for agent in weather_agent.yaml population_agent.yaml aggregate_agent.yaml city_founding_date_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done

for flow_tool in collaborator_agents_flow.py; do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool}
done

for agent in get_city_facts_agent.yaml; do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done








