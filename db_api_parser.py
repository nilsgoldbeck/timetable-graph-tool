import datetime
import json
import requests
import urllib.parse
from timetable import timetable

class db_api_parser():

    def __init__(self, api_key):
        self.api_key = api_key


    def get_timetable(self, begin, end, stop_categories, trip_categories):

        stops = {}
        trips = {}

        #TODO get stops

        #TODO get trips

        return timetable(begin, stops, trips)