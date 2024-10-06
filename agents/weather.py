import aiohttp
import requests
from F import LIST, DICT
from config import env

async def get_air_quality(zip:str):
    API_KEY = env('AIRNOW_API_KEY')  # Replace with your AirNow API key
    ZIP_CODE = zip        # Example ZIP code
    DISTANCE = '25'           # Search radius in miles
    URL = (
        'https://www.airnowapi.org/aq/observation/zipCode/current/'
        f'?format=application/json&zipCode={ZIP_CODE}&distance={DISTANCE}&API_KEY={API_KEY}'
    )
    result = ""
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as resp:
            if resp.status != 200:
                error = await resp.json()
                raise Exception(f"Error from AirNow: {error}")
            response_data = await resp.json()
            for observation in response_data:
                result += f"Location: {observation['ReportingArea']}, {observation['StateCode']}\nAir Quality: [ {observation['Category']['Name']} ] Level: [ {observation['Category']['Number']} ]\n"
            return result

def get_weather_by_zip(zip_code):
    # Step 1: Get latitude and longitude from ZIP code
    response = requests.get(f'http://api.zippopotam.us/us/{zip_code}')
    data = response.json()
    latitude = data['places'][0]['latitude']
    longitude = data['places'][0]['longitude']

    # Step 2: Get grid points
    response = requests.get(f'https://api.weather.gov/points/{latitude},{longitude}')
    forecast_url = response.json()['properties']['forecast']

    # Step 3: Get weather forecast
    response = requests.get(forecast_url)
    forecast_data = response.json()

    # Extract and display data
    periods = forecast_data['properties']['periods']
    results = []
    if periods:
        for p in periods:
            temp = f"""
                Weather for {p['name']}: {g('shortForecast', p)}
                Condition: {g('detailedForecast', p)}
                Temperature: {g('temperature', p)}°{g('temperatureUnit', p)}
                Wind: {g('windSpeed', p)}, {g('windDirection', p)}
                Chance of Rain: {g('value', p)}%
            """
            print(temp)
            results.append(temp)
        return results

def g(key, dic):
    return DICT.get(key, dic, "No Data Available")
"""
{
'detailedForecast': 'A chance of rain showers before 10pm. Mostly cloudy, with a low around 62. Northwest wind 0 to 5 mph. Chance of precipitation is 30%. New rainfall amounts less than a tenth of an inch possible.', 
'endTime': '2024-09-30T06:00:00-05:00', 
'icon': 'https://api.weather.gov/icons/land/night/rain_showers,30/bkn?size=medium', 
'isDaytime': False, 
'name': 'Tonight', 
'number': 1,
'probabilityOfPrecipitation': {'unitCode': 'wmoUnit:percent', 'value': 30}, 
'shortForecast': 'Chance Rain Showers then Mostly Cloudy', 
'startTime': '2024-09-29T18:00:00-05:00', 
'temperature': 62, 
'temperatureTrend': '', 
'temperatureUnit': 'F', 
'windDirection': 'NW', 
'windSpeed': '0 to 5 mph'
 }
"""
# get_weather_by_zip('84098')