import json
import datetime
from difflib import get_close_matches
from geopy import distance
from graph_tool.all import *

class timetable:

    def __init__(self, begin, end, trips = {}):
        self.begin = begin
        self.end = end
        self.trips = trips

    def load_trips_from_file(self, filename):

        with open(filename, 'r') as f:
            self.trips = json.load(f)


    def get_locations_from_trips(self, trips, max_transfer_distance):

        locations = {}

        print('Generating locations from trips')

        for trip_name, trip_list in trips.items():

            print('Adding locations for {}'.format(trip_name + ' '*50), end='\r')

            for trip in trip_list:

                for stop in trip:

                    eva_number = stop['loc_id']

                    if eva_number not in locations:

                        new_location = {'name': stop['loc_name'], 
                            'lat': stop['lat'], 'lon': stop['lon'],
                            'within_transfer_distance': []}

                        for existing_id, existing_location in locations.items():

                            p1 = (float(existing_location['lat']), float(existing_location['lon']))
                            p2 = (float(new_location['lat']), float(new_location['lon']))
                            d = distance.distance(p1, p2).meters

                            if d < max_transfer_distance:
                                new_location['within_transfer_distance'].append(existing_id)

                        for neighbour_id in new_location['within_transfer_distance']:
                            locations[neighbour_id]['within_transfer_distance'].append(eva_number)

                        locations[eva_number] = new_location

        return locations


    def add_transfer_edges(self, min_transfer_time, max_transfer_time):

        print('\nGenerating transfer links (transfer time {} to {} minutes)'.format(
            min_transfer_time, max_transfer_time))

        for loc_id, loc in self.locations.items():

            print('Adding transfers at {}'.format(loc['name'] + ' '*50), end='\r')

            for arr_time, arr_vertice in self.arrival_vertices[loc_id].items():
                for conn_loc_id in ([loc_id] + loc['within_transfer_distance']):
                    for dep_time, dep_vertice in self.departure_vertices[conn_loc_id].items():

                        if dep_time > arr_time + min_transfer_time:
                            if dep_time < arr_time + max_transfer_time:

                                self.add_edge(arr_vertice, dep_vertice, False, False, True)



    def generate_graph(self, max_transfer_distance, min_transfer_time, max_transfer_time):

        self.g = self.initialize_graph()

        self.locations = self.get_locations_from_trips(self.trips, max_transfer_distance)

        self.departure_vertices = {}
        self.arrival_vertices = {}

        for loc_id, loc in self.locations.items():
            self.departure_vertices[loc_id] = {}
            self.arrival_vertices[loc_id] = {}

        # Add trips:

        print('\nGenerating nodes and vertices from trips')

        for trip_name, trip_list in self.trips.items():

            for trip in trip_list:

                origin = trip[0]
                destination = trip[-1]

                print('Adding nodes and vertices for {}      '.format(trip_name), end='\r')

                # Add origin:

                dep_vertice = self.add_vertice(origin['loc_id'], origin['loc_name'],
                    self.get_timestamp(origin['dep_time']),
                    origin['lat'], origin['lon'], is_departure=True)

                # Add stops:

                for i in range(1, len(trip) - 1):

                    stop = trip[i]  

                    arr_vertice = self.add_vertice(stop['loc_id'], stop['loc_name'],
                        self.get_timestamp(stop['arr_time']),
                        stop['lat'], stop['lon'], is_departure=False)

                    self.add_edge(dep_vertice, arr_vertice, True, False, False,
                        stop['trip_id'], stop['trip_type'], origin['loc_id'], origin['loc_name'],
                        destination['loc_id'], destination['loc_name'])

                    dep_vertice = self.add_vertice(stop['loc_id'], stop['loc_name'],
                        self.get_timestamp(stop['dep_time']),
                        stop['lat'], stop['lon'], is_departure=True)

                    self.add_edge(arr_vertice, dep_vertice, True, True, False,
                        stop['trip_id'], stop['trip_type'], origin['loc_id'], origin['loc_name'],
                        destination['loc_id'], destination['loc_name'])

                # Add destination:
                
                arr_vertice = self.add_vertice(destination['loc_id'], destination['loc_name'],
                    self.get_timestamp(destination['arr_time']),
                    destination['lat'], destination['lon'], is_departure=False)

                self.add_edge(dep_vertice, arr_vertice, True, False, False,
                        stop['trip_id'], stop['trip_type'], origin['loc_id'], origin['loc_name'],
                        destination['loc_id'], destination['loc_name'])


        # Add transfers:

        self.add_transfer_edges(min_transfer_time, max_transfer_time)

        return self.g


    def initialize_graph(self):

        g = Graph()

        g.vp.loc_id = g.new_vertex_property('int')
        g.vp.loc_name = g.new_vertex_property('string')
        g.vp.time = g.new_vertex_property('int')
        g.vp.pos = g.new_vertex_property('vector<double>')
        g.vp.lat = g.new_vertex_property('double')
        g.vp.lon = g.new_vertex_property('double')
        g.vp.is_departure = g.new_vertex_property('bool')

        g.ep.duration = g.new_edge_property('int')
        g.ep.is_transport = g.new_edge_property('bool')
        g.ep.is_stationary = g.new_edge_property('bool')
        g.ep.is_transfer = g.new_edge_property('bool')
        g.ep.transport_id = g.new_edge_property('string')
        g.ep.transport_type = g.new_edge_property('string')
        g.ep.transport_origin_id = g.new_edge_property('string')
        g.ep.transport_origin_name = g.new_edge_property('string')
        g.ep.transport_destination_id = g.new_edge_property('string')
        g.ep.transport_destination_name = g.new_edge_property('string')

        return g


    def add_vertice(self, loc_id, loc_name, time, lat, lon, is_departure=True):

        v = None

        if is_departure:
            if time in self.departure_vertices[loc_id]:
                return self.departure_vertices[loc_id][time]
        else:
            if time in self.arrival_vertices[loc_id]:
                return self.arrival_vertices[loc_id][time]


        v = self.g.add_vertex()

        self.g.vp.loc_id[v] = loc_id
        self.g.vp.loc_name[v] = loc_name
        self.g.vp.time[v] = time
        self.g.vp.pos[v] = (lon, lat)
        self.g.vp.lat[v] = lat
        self.g.vp.lon[v] = lon
        self.g.vp.is_departure[v] = is_departure

        if is_departure:
            self.departure_vertices[loc_id][time] = v
        else:
            self.arrival_vertices[loc_id][time] = v

        return v


    def add_edge(self, v1, v2, is_transport, is_stationary, is_transfer, transport_id = None, transport_type = None, origin_id = None,
        origin_name = None, destination_id = None, destination_name = None):

        e = self.g.add_edge(v1, v2)

        self.g.ep.duration[e] = self.g.vp.time[v2] - self.g.vp.time[v1]
        self.g.ep.is_transport[e] = is_transport
        self.g.ep.is_stationary[e] = is_stationary
        self.g.ep.is_transfer[e] = is_transfer
        self.g.ep.transport_id[e] = transport_id
        self.g.ep.transport_type[e] = transport_type
        self.g.ep.transport_origin_id[e] = origin_id
        self.g.ep.transport_origin_name[e] = origin_name
        self.g.ep.transport_destination_id[e] = destination_id
        self.g.ep.transport_destination_name[e] = destination_name

        return e


    def get_timestamp(self, time_str):

        time = datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S')

        timestamp = int((time - self.begin).total_seconds() / 60)

        return timestamp


    def print_summary(self):

        print('Locations: {}'.format(len(self.locations)))
        print('Vertices: {}'.format(self.g.num_vertices()))
        print('Edges: {}'.format(self.g.num_edges()))

        self.g.set_edge_filter(self.g.ep.is_transport)
        print('On-tranport edges: {}'.format(self.g.num_edges()))

        self.g.set_edge_filter(self.g.ep.is_stationary)
        print('Stationary on-tranport edges: {}'.format(self.g.num_edges()))

        self.g.set_edge_filter(self.g.ep.is_transfer)
        print('Transfer edges: {}'.format(self.g.num_edges()))

        self.g.clear_filters()


    def search_location(self, search_string):

        loc_names = [v['name'] for k, v in self.locations.items()]

        result =  get_close_matches(search_string, loc_names, n=1)

        loc_name_found = result[0]

        loc_id_found = next((x[0] for x in self.locations.items() if x[1]['name'] == loc_name_found), None)

        return loc_name_found, loc_id_found


    def find_route(self, from_loc_id, to_loc_id, dep_time):

        dep_timestamp = self.get_timestamp(dep_time.isoformat())

        origin_vertice = self.g.add_vertex()
        destination_vertice = self.g.add_vertex()

        boarding_edges = []

        for t, v in self.departure_vertices[from_loc_id].items():
            if t > dep_timestamp:
                #e = self.add_edge(origin_vertice, v, False, False, False)
                e = self.g.add_edge(origin_vertice, v)
                self.g.ep.duration[e] = t - dep_timestamp
                boarding_edges.append(e)

        
        alighting_edges = []

        for t, v in self.arrival_vertices[to_loc_id].items():
            #e = self.add_edge(v, destination_vertice, False, False, False)
            e = self.g.add_edge(v, destination_vertice)
            self.g.ep.duration[e] = 0
            alighting_edges.append(e)

        
        shortest_paths = graph_tool.topology.all_shortest_paths(self.g, origin_vertice,
            destination_vertice, weights=self.g.ep.duration)

        for e in (boarding_edges + alighting_edges):
            self.g.remove_edge(e)

        #self.g.remove_vertex(origin_vertice)
        #self.g.remove_vertex(destination_vertice)

        return shortest_paths
