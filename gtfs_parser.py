import partridge as ptg
import pandas as pd
import datetime as dt
from shapely import wkt
import timetable_graph as tg

class gtfs_parser():

    def __init__(self, gtfs_path):
        self.gtfs_path = gtfs_path


    def get_service_ids(self, date):

        service_ids_by_date = ptg.read_service_ids_by_date(self.gtfs_path)

        return service_ids_by_date[date]


    def get_busiest_date(self):

        return ptg.read_busiest_date(self.gtfs_path)[0]


    def get_trips(self, service_ids):

        view = {
            'trips.txt': {'service_id': service_ids}
        }

        df = ptg.load_geo_feed(self.gtfs_path, view).trips

        df = df.set_index('trip_id')

        return df


    def get_stop_times(self, trip_ids):

        view = {
            'stop_times.txt': {'trip_id': trip_ids}
        }

        df = ptg.load_geo_feed(self.gtfs_path, view).stop_times

        df = df.set_index(['trip_id', 'stop_sequence'])

        return df


    def get_stops(self, stop_ids):

        view = {
            'stops.txt': {'stop_id': stop_ids}
        }

        df = ptg.load_geo_feed(self.gtfs_path, view).stops

        df = df.set_index('stop_id')

        return df


    def get_transfers(self, stop_ids):

        view = {
            'transfers.txt': {'from_stop_id': stop_ids}
        }

        df = ptg.load_geo_feed(self.gtfs_path, view).transfers

        df = df.set_index(['from_stop_id', 'to_stop_id'])

        return df


    def read_gtfs_feed(self, date):

        self.date = date

        print('Starting GTFS import for {}'.format(date))

        self.service_ids = self.get_service_ids(date)
        print('Imported {} services'.format(len(self.service_ids)))

        self.trips = self.get_trips(self.service_ids)
        print('Imported {} trips'.format(len(self.trips)))

        self.stop_times = self.get_stop_times(self.trips.index.values)
        print('Imported {} stop times'.format(len(self.stop_times)))

        self.stops = self.get_stops(self.stop_times['stop_id'].unique())
        print('Imported {} stops'.format(len(self.stops)))

        self.transfers = self.get_transfers(self.stop_times['stop_id'].unique())
        print('Imported {} transfer links'.format(len(self.transfers)))

        print('GTFS import complete')


    def get_timetable_graph(self, min_transfer_time, max_transfer_time):
        
        begin = dt.datetime.combine(self.date, dt.time(0, 0))
        end = dt.datetime.combine(self.date, dt.time(23, 59))

        print('Generating timetable graph')
        timetable = tg.timetable_graph(begin, end)
        

        for index, row in self.stops.iterrows():
            timetable.add_location(index, row['stop_name'], row['geometry'].coords[0][1],row['geometry'].coords[0][0])
        print('Added {} locations'.format(len(self.stops)))

        counter = 0
        for trip_id, trip_df in self.stop_times.groupby(level=0):

            trip_name = self.trips.loc[trip_id]['route_id']

            loc_ids = []
            arr_times = []
            dep_times = []

            loc_ids.append(trip_df.loc[trip_id, 1]['stop_id'])
            dep_times.append(self.timedate_from_timestamp(trip_df.loc[trip_id, 1]['departure_time'], begin))

            for i in range(2, len(trip_df)):
                loc_ids.append(trip_df.loc[trip_id, i]['stop_id'])
                arr_times.append(self.timedate_from_timestamp(trip_df.loc[trip_id, i]['arrival_time'], begin))
                dep_times.append(self.timedate_from_timestamp(trip_df.loc[trip_id, i]['departure_time'], begin))

            arr_times.append(self.timedate_from_timestamp(trip_df.loc[trip_id, len(trip_df)]['arrival_time'], begin))

            timetable.add_trip(loc_ids, dep_times, arr_times, trip_id, trip_name)
            counter += 1

            if counter % 1000 == 0:
                print('Added {} trips'.format(counter), end='\r')

        print('Added {} trips'.format(counter))


        for transfer_id, transfer_type in self.transfers.iterrows():
            timetable.add_transfer(transfer_id[0], transfer_id[1], min_transfer_time, max_transfer_time)
        print('Added {} transfer options'.format(len(self.transfers)))

        return timetable


    def timedate_from_timestamp(self, timestamp, reference_datetime):

            return reference_datetime + dt.timedelta(minutes=timestamp)