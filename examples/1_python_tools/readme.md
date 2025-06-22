# Customer care example
This example was written to simulate a customer care agent for hospital. It is capable of
querying remote apis with dummy data related to a nearby healthcare providers (limit queries to Lowell, MA)
and 

## Steps to import
1. Run `orchestrate server start -e .my-env`
2. Signup for a Sevice Now account at https://developer.servicenow.com/dev.do
2. Validate your email address (check email)
3. On the landing page click start building. This will allocate a new instance of SNOW for you. 
4. Back on the landing page, click your profile icon on the top right and under "My instance" click manage instance password.
5. Create an application connection using these credentials
```bash
orchestrate connections add -a service-now
orchestrate connections configure -a service-now --env draft --type team --kind basic --url <the instance url>
orchestrate connections set-credentials -a service-now --env draft -u admin -p <password from modal>
```
6. Run `pip install -r tools/requirements.txt`
6. Run the import all script `./import-all.sh`
7. Run `orchestrate chat start`

## Suggested script
- Show me my benefits related to mental health
- Show me my open claims
- I need help to find a doctor for my son's ear pain near Lowell
<br>

- I need help generating my benefits' documentation. Can you open a ticket.
- Show me incident number <the incident number from the output of the previous utterance>

