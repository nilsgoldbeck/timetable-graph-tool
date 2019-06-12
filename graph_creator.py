import datetime
import json
import requests
import urllib.parse

def load_header():
    
    with open('db-api-header.json', 'r') as f:
        header = json.load(f)

    if header:
        return header
    else:
        raise Exception("Could not load API header")


def get_stations(header, categories):

    url = "https://api.deutschebahn.com/stada/v2/stations"
    data = {'category': categories}

    response = requests.get(url, data, headers=header)

    return response.json()['result']


def get_main_eva_number(station):

    for number in station['evaNumbers']:
        if number['isMain']:
            return number['number']

def get_departures(header, eva_number, datetime):

    url = "https://api.deutschebahn.com/fahrplan-plus/v1/departureBoard/" + str(eva_number)
    data = {'date': datetime.isoformat()}

    response = requests.get(url, data, headers=header)

    assert response.status_code == 200

    return response.json()


def get_journey(header, details_id):

    url = "https://api.deutschebahn.com/fahrplan-plus/v1/journeyDetails/" + urllib.parse.quote(details_id)

    response = requests.get(url, headers=header)

    if response.status_code == 200:
        return response.json()
    else:
        return ""


def create_graph(date, station_categories, hour_from, hour_to):

    header = load_header()

    stations = get_stations(header, station_categories)

    for station in stations:

        eva_number = get_main_eva_number(station)

        print(station['name'])
        print(eva_number)

        for hour in range(hour_from, hour_to):

            time = datetime.time(hour,0)

            dt = datetime.datetime.combine(date, time)

            departures = get_departures(header, eva_number, dt)

            for departure in departures:

                dep_time = datetime.datetime.strptime(departure['dateTime'], "%Y-%m-%dT%H:%M")

                if dep_time.hour == hour:

                    details_id = departure['detailsId']

                    journey = get_journey(header, details_id)

                    if journey != "":
                        print(str(dep_time.strftime("%H:%M")) + " " + departure['name'] + " to " + journey[-1]['stopName'])

                        for stop in journey:
                            stop_time = stop['arrTime'] if 'arrTime' in stop else stop['depTime']
                            print("  " + stop_time + " " + stop['stopName'])


    return

