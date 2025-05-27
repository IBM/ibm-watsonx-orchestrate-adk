#!/usr/bin/env bash

orchestrate env activate local
for tool in get_weather_data get_population_data aggregate_data get_city_founding_date; do
  orchestrate tools remove -n ${tool}
done

for agent in weather_agent get_city_facts_agent population_agent aggregate_agent city_founding_date_agent; do
  orchestrate agents remove -n ${agent} -k native
done


orchestrate tools remove -n collaborator_agents_flow