from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from pydantic import BaseModel, Field
import requests
class WeatherData(BaseModel):
    wind_speed: float = Field(description="Wind Speed")
    temperature: float = Field(description="Temperature")
    current_weather: str = Field(description="Current Weather")

@tool(
    permission=ToolPermission.READ_ONLY
)
def get_weather_data(city: str) -> WeatherData:
    """
    Return a WeatherData object
    Args:
        city (str): inputted city

    Returns:
        WeatherData: A WeatherData object
    """
    cities = {
        "New York" : {"latitude" : "40.7128","longitude" : "-74.0060"},
        "Los Angeles" : {"latitude" : "34.0522","longitude" : "118.2437"},
        "San Jose" : {"latitude" : "37.7749","longitude" : "122.4194"},
        "Fremont" : {"latitude" : "37.5485","longitude" : "121.9886"},
    }
    weather_conditions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog and depositing rime fog",
        48: "Fog and depositing rime fog",
        51: "Drizzle: Light intensity",
        53: "Drizzle: Moderate intensity",
        55: "Drizzle: Dense intensity",
        56: "Freezing Drizzle: Light intensity",
        57: "Freezing Drizzle: Dense intensity",
        61: "Rain: Slight intensity",
        63: "Rain: Moderate intensity",
        65: "Rain: Heavy intensity",
        66: "Freezing Rain: Light intensity",
        67: "Freezing Rain: Heavy intensity",
        71: "Snow fall: Slight intensity",
        73: "Snow fall: Moderate intensity",
        75: "Snow fall: Heavy intensity",
        77: "Snow grains",
        80: "Rain showers: Slight intensity",
        81: "Rain showers: Moderate intensity",
        82: "Rain showers: Violent intensity",
        85: "Snow showers: Slight intensity",
        86: "Snow showers: Heavy intensity",
        95: "Thunderstorm: Slight or moderate",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }
    if city not in cities.keys(): 
        city =cities['San Jose']
    url = f"https://api.open-meteo.com/v1/forecast?latitude={cities[city]['latitude']}&longitude={cities[city]['longitude']}&current_weather=true"

    response = requests.get(url)

    if response.status_code == 200:
        weather_data = response.json()
        current_weather = weather_data.get('current_weather', {})
        temperature = current_weather.get('temperature', 'N/A')
        wind_speed = current_weather.get('windspeed', 'N/A')
        weather_code = current_weather.get('weathercode', 'N/A')

        return WeatherData(wind_speed=wind_speed,
            temperature=temperature,
            current_weather=weather_conditions[weather_code].lower() if weather_code in weather_conditions.keys() else "UNKNOWN")
    return WeatherData(wind_speed=22.2,
        temperature=75,
        current_weather=weather_conditions[weather_code] if weather_code in weather_conditions.keys() else "UNKNOWN")

