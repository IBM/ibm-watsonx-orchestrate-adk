# Customer care example
This example was written to simulate a customer care agent for hospital. It is capable of
querying remote apis with dummy data related to a nearby healthcare providers (limit queries to Lowell, MA)
and 

## Steps to import
1. Run `orchestrate server start -e .my-env`
2. Run `pip install -r tools/requirements.txt`
3. Run the import all script `./import-all.sh`
4. Run `orchestrate chat start`

## Suggested script
- Show me my benefits related to mental health
- Show me my open claims
- I need help to find a doctor for my son's ear pain near Lowell
<br>

- I need help generating my benefits' documentation. Can you open a ticket.
- Show me incident number <the incident number from the output of the previous utterance>

