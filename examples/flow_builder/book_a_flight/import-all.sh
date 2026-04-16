orchestrate env activate local
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for flow_tool in $(ls "${SCRIPT_DIR}/tools"); do
  orchestrate tools import -k flow -f ${SCRIPT_DIR}/tools/${flow_tool} 
done

# import hello message agent
for agent in $(ls "${SCRIPT_DIR}/agents"); do
  orchestrate agents import -f ${SCRIPT_DIR}/agents/${agent}
done
