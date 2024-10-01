import requests
from F import LIST, DICT


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