import datetime as dt
from time import sleep
import json
import requests
import urllib.parse
from timetable import timetable

class db_api_parser():

    url_stations = "https://api.deutschebahn.com/stada/v2/stations"
    url_departures = "https://api.deutschebahn.com/fahrplan-plus/v1/departureBoard/"
    url_journey_details = "https://api.deutschebahn.com/fahrplan-plus/v1/journeyDetails/"

    max_wait_time = 1
    time_increment = 240

    def __init__(self, api_key):
        self.api_key = api_key

        self.departure_request_times = []
        self.trip_request_times = []

    def get_timetable(self, start, end, stop_categories = '1-7'):

        self.header = self.get_header()

        eva_numbers = self.get_eva_numbers(stop_categories)

        trips = self.get_trips(start, end, eva_numbers)

        return timetable(start, end, trips)


    def get_header(self):

        return { "Accept": "application/json", "Authorization": "Bearer " + self.api_key }


    def get_eva_numbers(self, categories):

        data = {'category': categories}

        response = requests.get(self.url_stations, data, headers=self.header)

        eva_numbers = []

        for station in response.json()['result']:
            for number in station['evaNumbers']:
                eva_numbers.append(number['number'])

        return eva_numbers


    def get_departures(self, eva_number, datetime):

        url = self.url_departures + str(eva_number)
        data = {'date': datetime.isoformat()}

        try:
            self.count_dep_requests += 1
            response = requests.get(url, data, headers=self.header, timeout=self.max_wait_time)
        except (requests.Timeout):
            self.count_dep_requests_timeout += 1
            return
        except (requests.ConnectionError):
            self.count_dep_requests_failed += 1
            return

        #self.departure_request_times.append(response.elapsed.total_seconds())

        if response.status_code is not 200:
            self.count_dep_requests_failed += 1
            return

        departures = []

        for departure in response.json():

            dep_time = dt.datetime.strptime(departure['dateTime'], "%Y-%m-%dT%H:%M")
            
            departures.append({'trip_id': departure['name'], 'loc_id': eva_number, 'dep_time': dep_time, 'details_id': departure['detailsId']})

        return departures


    def get_journey_details(self, departure):

        url = self.url_journey_details + urllib.parse.quote(departure['details_id'])

        try:
            self.count_trip_requests += 1
            response = requests.get(url, headers=self.header, timeout=self.max_wait_time)
        except (requests.Timeout):
            self.count_trip_requests_timeout += 1
            return
        except (requests.ConnectionError):
            self.count_trip_requests_failed += 1
            return

        #self.trip_request_times.append(response.elapsed.total_seconds())

        if response.status_code is not 200:
            self.count_trip_requests_failed += 1
            return

        stops = response.json()

        if stops[0]['stopId'] == departure['loc_id']:

            trip = []

            current_datetime = departure['dep_time']

            for stop in stops:

                if 'arrTime' in stop:
                    arr_time = dt.datetime.strptime(stop['arrTime'], '%H:%M').time()
                    arr_time = dt.datetime.combine(current_datetime.date(), arr_time)
                    if arr_time < current_datetime:
                        arr_time = arr_time + dt.timedelta(days=1)
                    current_datetime = arr_time
                    arr_time = arr_time.isoformat()
                else:
                    arr_time = None

                if 'depTime' in stop:
                    dep_time = dt.datetime.strptime(stop['depTime'], '%H:%M').time()
                    dep_time = dt.datetime.combine(current_datetime.date(), dep_time)
                    if dep_time < current_datetime:
                        dep_time = dep_time + dt.timedelta(days=1)
                    current_datetime = dep_time
                    dep_time = dep_time.isoformat()
                else:
                    dep_time = None      

                trip.append({'loc_id': stop['stopId'], 'loc_name': stop['stopName'], 'dep_time': dep_time, 'arr_time': arr_time,
                    'lat': stop['lat'], 'lon': stop['lon'], 'trip_id': stop['train'], 'trip_type': stop['type']})

            return trip


    def get_trips(self, start, end, eva_numbers):

        trips = {}

        self.count_dep_requests = 0
        self.count_dep_requests_timeout = 0
        self.count_dep_requests_failed = 0
        self.count_trip_requests = 0
        self.count_trip_requests_timeout = 0
        self.count_trip_requests_failed = 0
        self.count_evas_complete = 0

        for eva_number in eva_numbers:

            current_time = start

            while current_time < end:

                print('Gathering trips from {} at {}. Completed {} of {} stops. Gathered {} trips.'.format(
                    eva_number, current_time, self.count_evas_complete, len(eva_numbers), len(trips)), end='\r')

                departures = self.get_departures(eva_number, current_time)

                if departures is None:
                    current_time += dt.timedelta(minutes=self.time_increment)
                    continue

                for departure in departures:
                    
                    trip_id = departure['trip_id']

                    if trip_id not in trips:
                        trips[trip_id] = []

                    trip = self.get_journey_details(departure)

                    if trip is not None:
                        trips[trip_id].append(trip)

                if len(departures) > 0:
                    current_time = departures[-1]['dep_time'] + dt.timedelta(minutes=1)
                else:
                    current_time = current_time + dt.timedelta(minutes=self.time_increment)

            self.count_evas_complete += 1

        print('\n')
        print('Departure board API:')
        print('Requests: {}'.format(self.count_dep_requests))
        print('Timeout: {}'.format(self.count_dep_requests_timeout))
        print('Failed: {}'.format(self.count_dep_requests_failed))

        print('\n')
        print('Journey details API:')
        print('Requests: {}'.format(self.count_trip_requests))
        print('Timeout: {}'.format(self.count_trip_requests_timeout))
        print('Failed: {}'.format(self.count_trip_requests_failed))

        print('\n')
        print('{} trips gathered'.format(len(trips)))

        return trips


    def save_trips_to_file(self, trips, filename):

        with open(filename, 'w') as f:
            json.dump(trips, f)
