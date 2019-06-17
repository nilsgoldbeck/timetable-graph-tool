import partridge as ptg
from timetable import timetable

class gtfs_parser():

    def __init__(self, gtfs_path):
        self.gtfs_path = gtfs_path


    def service_ids(self, date):

        service_ids_by_date = ptg.read_service_ids_by_date(self.gtfs_path)

        return service_ids_by_date[date]


    def get_busiest_date(self):

        return ptg.read_busiest_date(self.gtfs_path)

    def get_feed(self, service_ids):

        view = {
            'trips.txt': {'service_id': service_ids}
        }

        return ptg.load_geo_feed(self.gtfs_path, view)