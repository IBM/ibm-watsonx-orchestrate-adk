from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType, ExpectedCredentials

from typing import List


@tool(
    name="get_continents",
    description="get a list of continents",
    permission=ToolPermission.READ_ONLY
)
def get_continents() -> List[str]:
    """
    Retrieves a list of continents
    :returns: a list of continents
    """
    return [
        "Africa",
        "Antarctica",
        "Asia",
        "Europe",
        "North America",
        "Oceania",
        "South America"
    ]

@tool(
    name="get_countries_by_continent",
    description="Get the list of countries for the specified contient",
    permission=ToolPermission.READ_ONLY
)
def get_countries_by_continent(continent: str) -> List[str]:
    """
    Retrieves the list of countries for the specified continent
    :param: continent: A continent
    :returns: a list of countries
    """
    continent_map = {
        "Africa": [
            "Algeria","Angola","Benin","Botswana","Burkina Faso","Burundi",
            "Cabo Verde","Cameroon","Central African Republic","Chad","Comoros",
            "Congo (Congo-Brazzaville)","Djibouti","Egypt","Equatorial Guinea",
            "Eritrea","Eswatini","Ethiopia","Gabon","Gambia","Ghana","Guinea",
            "Guinea-Bissau","Kenya","Lesotho","Liberia","Libya","Madagascar",
            "Malawi","Mali","Mauritania","Mauritius","Morocco","Mozambique",
            "Namibia","Niger","Nigeria","Rwanda","Sao Tome and Principe",
            "Senegal","Seychelles","Sierra Leone","Somalia","South Africa",
            "South Sudan","Sudan","Tanzania","Togo","Tunisia","Uganda",
            "Zambia","Zimbabwe"
        ],
        "Europe": [
            "Albania","Andorra","Austria","Belarus","Belgium",
            "Bosnia and Herzegovina","Bulgaria","Croatia","Cyprus",
            "Czechia (Czech Republic)","Denmark","Estonia","Finland","France",
            "Germany","Greece","Hungary","Iceland","Ireland","Italy","Latvia",
            "Liechtenstein","Lithuania","Luxembourg","Malta","Moldova","Monaco",
            "Montenegro","Netherlands","North Macedonia","Norway","Poland",
            "Portugal","Romania","Russia","San Marino","Serbia","Slovakia",
            "Slovenia","Spain","Sweden","Switzerland","Ukraine",
            "United Kingdom","Vatican City"
        ],
        "Asia": [
            "Afghanistan","Armenia","Azerbaijan","Bahrain","Bangladesh","Bhutan",
            "Brunei","Cambodia","China","Georgia","India","Indonesia","Iran",
            "Iraq","Israel","Japan","Jordan","Kazakhstan","Kuwait","Kyrgyzstan",
            "Laos","Lebanon","Malaysia","Maldives","Mongolia","Myanmar (Burma)",
            "Nepal","North Korea","Oman","Pakistan","Philippines","Qatar",
            "Saudi Arabia","Singapore","South Korea","Sri Lanka","Syria",
            "Tajikistan","Thailand","Timor-Leste","Turkey","Turkmenistan",
            "United Arab Emirates","Uzbekistan","Vietnam","Yemen"
        ],
        "North America": [
            "Antigua and Barbuda","Bahamas","Barbados","Belize","Canada",
            "Costa Rica","Cuba","Dominica","Dominican Republic","El Salvador",
            "Grenada","Guatemala","Haiti","Honduras","Jamaica","Mexico",
            "Nicaragua","Panama","Saint Kitts and Nevis","Saint Lucia",
            "Saint Vincent and the Grenadines","Trinidad and Tobago",
            "United States"
        ],
        "South America": [
            "Argentina","Bolivia","Brazil","Chile","Colombia","Ecuador",
            "Guyana","Paraguay","Peru","Suriname","Uruguay","Venezuela"
        ],
        "Oceania": [
            "Australia","Fiji","Kiribati","Marshall Islands","Micronesia",
            "Nauru","New Zealand","Palau","Papua New Guinea","Samoa",
            "Solomon Islands","Tonga","Tuvalu","Vanuatu"
        ]
    }

    # Normalize input (case-insensitive)
    continent = continent.strip().title()
    return continent_map.get(continent, [])


def main():
    print("python main function")
    print(get_countries_by_continent ("Africa"))

if __name__ == "__main__":
    main()