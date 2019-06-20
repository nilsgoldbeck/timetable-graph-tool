import datetime as dt
from graph_tool.all import *
from difflib import get_close_matches
from geopy import distance

class timetable_graph:

    def __init__(self, begin=None, end=None):     

        self.g = Graph()

        self.g.gp.begin = self.g.new_graph_property('object')
        self.g.gp.begin = begin

        self.g.gp.end = self.g.new_graph_property('object')
        self.g.gp.end = end

        self.g.gp.locations = self.g.new_graph_property('object')
        self.g.gp.locations = {}

        self.g.gp.departure_vertices = self.g.new_graph_property('object')
        self.g.gp.departure_vertices = {}

        self.g.gp.arrival_vertices = self.g.new_graph_property('object')
        self.g.gp.arrival_vertices = {}

        self.g.gp.trips = self.g.new_graph_property('object')
        self.g.gp.trips = {}

        self.g.vp.loc_id = self.g.new_vertex_property('int')
        self.g.vp.timestamp = self.g.new_vertex_property('int')
        self.g.vp.pos = self.g.new_vertex_property('vector<double>')
        self.g.vp.is_departure = self.g.new_vertex_property('bool')

        self.g.ep.duration = self.g.new_edge_property('int')
        self.g.ep.is_transport = self.g.new_edge_property('bool')
        self.g.ep.is_stationary = self.g.new_edge_property('bool')
        self.g.ep.is_transfer = self.g.new_edge_property('bool')
        self.g.ep.trip_id = self.g.new_edge_property('string')
        self.g.ep.loc_id = self.g.new_edge_property('string')


    def add_location(self, loc_id, name, latitude, longitude):

        self.g.gp.locations[loc_id] = {
            'name': name, 
            'lat': latitude, 
            'lon': longitude
            }

        self.g.gp.departure_vertices[loc_id] = {}
        self.g.gp.arrival_vertices[loc_id] = {}


    def add_trip(self, loc_ids, dep_times, arr_times, trip_id, trip_name):

        self.g.gp.trips[trip_id] = { 
            'name': trip_name,
            'origin_loc_id': loc_ids[0],
            'destination_loc_id': loc_ids[-1]
            }

        current_vertex = self.add_vertex(loc_ids[0], dep_times[0])

        for i in range(len(loc_ids) - 2):

            arrival_vertex = self.add_vertex(loc_ids[i+1], arr_times[i], is_departure=False)

            self.add_edge(current_vertex, arrival_vertex, is_transport=True, trip_id=trip_id)

            current_vertex = arrival_vertex

            departure_vertex = self.add_vertex(loc_ids[i+1], dep_times[i+1])

            self.add_edge(current_vertex, departure_vertex, is_transport=True, is_stationary=True,
                trip_id=trip_id, loc_id=loc_ids[i+1])

            current_vertex = departure_vertex

        
        destination_vertex = self.add_vertex(loc_ids[-1], arr_times[-1], is_departure=False)

        self.add_edge(current_vertex, destination_vertex, is_transport=True, trip_id=trip_id)

        return


    def add_vertex(self, loc_id, datetime, is_departure=True):

        timestamp = self.timestamp_from_datetime(datetime)

        v = None

        if is_departure:
            if timestamp in self.g.gp.departure_vertices[loc_id]:
                return self.g.gp.departure_vertices[loc_id][timestamp]
        else:
            if timestamp in self.g.gp.arrival_vertices[loc_id]:
                return self.g.gp.arrival_vertices[loc_id][timestamp]


        v = self.g.add_vertex()

        self.g.vp.loc_id[v] = loc_id
        self.g.vp.timestamp[v] = timestamp
        self.g.vp.pos[v] = (self.g.gp.locations[loc_id]['lon'], self.g.gp.locations[loc_id]['lat'])
        self.g.vp.is_departure[v] = is_departure

        if is_departure:
            self.g.gp.departure_vertices[loc_id][timestamp] = v
        else:
            self.g.gp.arrival_vertices[loc_id][timestamp] = v

        return v


    def add_edge(self, v1, v2, is_transport=False, is_stationary=False, is_transfer=False, trip_id = None, loc_id = None):

        e = self.g.add_edge(v1, v2)

        self.g.ep.duration[e] = self.g.vp.timestamp[v2] - self.g.vp.timestamp[v1]
        self.g.ep.is_transport[e] = is_transport
        self.g.ep.is_stationary[e] = is_stationary
        self.g.ep.is_transfer[e] = is_transfer
        self.g.ep.trip_id[e] = trip_id
        self.g.ep.loc_id[e] = loc_id

        return e


    def add_transfer(self, from_loc_id, to_loc_id, min_transfer_time, max_transfer_time):
        
        for arr_timestamp, arr_vertice in self.g.gp.arrival_vertices[from_loc_id].items():
            for dep_timestamp, dep_vertice in self.g.gp.departure_vertices[to_loc_id].items():

                    if dep_timestamp > arr_timestamp + min_transfer_time:
                        if dep_timestamp < arr_timestamp + max_transfer_time:

                            self.add_edge(arr_vertice, dep_vertice, is_transfer=True)

        return



    def timestamp_from_iso_str(self, iso_str):

        datetime = dt.datetime.strptime(iso_str, '%Y-%m-%dT%H:%M:%S')

        return self.timestamp_from_datetime(datetime)


    def timestamp_from_datetime(self, datetime):
        
        if datetime < self.g.gp.begin:
            return None
        else:
            return int((datetime - self.g.gp.begin).total_seconds() / 60)


    def datetime_from_timestamp(self, timestamp):
        
        return self.g.gp.begin + dt.timedelta(minutes=timestamp)


    def save_to_file(self, filename):
        
        # Vertex objects cannot be pickled, thus convert to int:
        for loc_id, timestamps in self.g.gp.departure_vertices.items():
            for t, v in timestamps.items():
                self.g.gp.departure_vertices[loc_id][t] = int(v)

        for loc_id, timestamps in self.g.gp.arrival_vertices.items():
            for t, v in timestamps.items():
                self.g.gp.arrival_vertices[loc_id][t] = int(v)

        self.g.save(filename + '.gt')   


    def load_from_file(self, filename):
        
        self.g = load_graph(filename + '.gt')

        # Transform int back to vertice
        for loc_id, timestamps in self.g.gp.departure_vertices.items():
            for t, v in timestamps.items():
                self.g.gp.departure_vertices[loc_id][t] = self.g.vertex(v)

        for loc_id, timestamps in self.g.gp.arrival_vertices.items():
            for t, v in timestamps.items():
                self.g.gp.arrival_vertices[loc_id][t] = self.g.vertex(v)


    def find_location(self, search_str):

        loc_names = [v['name'] for k, v in self.g.gp.locations.items()]

        result =  get_close_matches(search_str, loc_names, n=1)

        if len(result) is 0:
            return None, None

        loc_name_found = result[0]

        loc_id_found = next((x[0] for x in self.g.gp.locations.items() if x[1]['name'] == loc_name_found), None)

        return loc_name_found, loc_id_found


    def find_shortest_paths(self, from_loc_id, to_loc_id, dep_time, max_num_paths):
        
        dep_timestamp = self.timestamp_from_datetime(dep_time)

        origin_vertex = self.g.add_vertex()
        destination_vertex = self.g.add_vertex()

        departure_edges = []

        for t, v in self.g.gp.departure_vertices[from_loc_id].items():
            if t > dep_timestamp:
                e = self.g.add_edge(origin_vertex, v)
                self.g.ep.duration[e] = t - dep_timestamp
                departure_edges.append(e)

        
        arrival_edges = []

        for t, v in self.g.gp.arrival_vertices[to_loc_id].items():
            e = self.g.add_edge(v, destination_vertex)
            self.g.ep.duration[e] = 0
            arrival_edges.append(e)

        
        shortest_paths = graph_tool.topology.all_shortest_paths(self.g, origin_vertex,
            destination_vertex, weights=self.g.ep.duration)

        for e in (departure_edges + arrival_edges):
            self.g.remove_edge(e)

        self.g.remove_vertex([destination_vertex, origin_vertex])        

        result = []

        for i in range(max_num_paths):
            try:
                result.append(next(shortest_paths))
            except StopIteration:
                break

        return result


    def find_path_between_coordinates(self, from_lat, from_lon, to_lat, to_lon, dep_time,
        max_num_paths=1, max_access_distance=250, access_speed=4):

        from_loc_access_times = {}
        to_loc_access_times = {}

        for k, v in self.g.gp.locations.items():

            distance_from_origin = distance.distance((v['lat'], v['lon']), (from_lat, from_lon)).meters

            if distance_from_origin < max_access_distance:
                from_loc_access_times[k] = distance_from_origin / 1000 / access_speed * 60

            distance_to_destination = distance.distance((v['lat'], v['lon']), (to_lat, to_lon)).meters
            if distance_to_destination < max_access_distance:
                to_loc_access_times[k] = distance_to_destination / 1000 / access_speed * 60

        dep_timestamp = self.timestamp_from_datetime(dep_time)

        origin_vertex = self.g.add_vertex()
        destination_vertex = self.g.add_vertex()

        departure_edges = []

        for from_loc_id, access_time in from_loc_access_times.items():
            for t, v in self.g.gp.departure_vertices[from_loc_id].items():
                if t > dep_timestamp + access_time:
                    e = self.g.add_edge(origin_vertex, v)
                    self.g.ep.duration[e] = t - dep_timestamp
                    departure_edges.append(e)

        
        arrival_edges = []

        for to_loc_id, access_time in to_loc_access_times.items():
            for t, v in self.g.gp.arrival_vertices[to_loc_id].items():
                e = self.g.add_edge(v, destination_vertex)
                self.g.ep.duration[e] = access_time
                arrival_edges.append(e)

        
        shortest_paths = graph_tool.topology.all_shortest_paths(self.g, origin_vertex,
            destination_vertex, weights=self.g.ep.duration)

        for e in (departure_edges + arrival_edges):
            self.g.remove_edge(e)

        self.g.remove_vertex([destination_vertex, origin_vertex])        

        result = []

        for i in range(max_num_paths):
            try:
                result.append(next(shortest_paths))
            except StopIteration:
                break

        return result


    def path_to_string_with_all_stops(self, path):

        result = ''

        for i in range(1, len(path) - 1):

            time = self.datetime_from_timestamp(self.g.vp.timestamp[path[i]])
            loc = self.g.gp.locations[str(self.g.vp.loc_id[path[i]])]['name']

            if self.g.vp.is_departure[path[i]]:

                trip_name = self.g.gp.trips[self.g.ep.trip_id[(path[i], path[i+1])]]['name']
                result += '{} DEP {} {}\n'.format(time, trip_name, loc)

            else:

                trip_name = self.g.gp.trips[self.g.ep.trip_id[(path[i-1], path[i])]]['name']
                result += '{} ARR {} {}\n'.format(time, trip_name, loc)
            
        return result


    def path_to_string(self, path):

        result = ''

        current_trip = ''

        for i in range(1, len(path) - 1):

            time = self.datetime_from_timestamp(self.g.vp.timestamp[path[i]])
            loc = self.g.gp.locations[str(self.g.vp.loc_id[path[i]])]['name']

            if self.g.vp.is_departure[path[i]]:

                trip_name = self.g.gp.trips[self.g.ep.trip_id[(path[i], path[i+1])]]['name']

                if trip_name != current_trip:
                    current_trip = trip_name
                    result += '{} DEP {} {}\n'.format(time, trip_name, loc)

            else:

                if i == len(path) - 2:
                    result += '{} ARR {} {}\n'.format(time, current_trip, loc)
                    return result

                if self.g.ep.is_transfer[(path[i], path[i+1])]:
                    result += '{} ARR {} {}\n'.format(time, current_trip, loc)
            
        return result
