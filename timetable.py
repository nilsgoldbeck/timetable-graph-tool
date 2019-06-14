from graph_tool.all import *

class timetable:

    def __init__(self, time_zero, stops, trips):
        self.time_zero = time_zero
        self.stops = stops
        self.trips = trips


    def generate_graph(self, min_transfer_time, max_transfer_time):

        self.g = self.initialize_graph()

        #TODO Add trips

        #TODO Add transfers

        pass


    def initialize_graph(self):

        g = Graph()

        #TODO Add vertex properties
        #station-name <string>
        #eva <short>
        #departure <bool>
        #arrival <bool>
        #time <short>
        #pos vector<double>
        #lat <double>
        #lon <double>

        #TODO Add edge properties
        #length <short>
        #transfer <bool>
        #train-stationary <bool>
        #train-travelling <bool>
        #train-id <string>
        #train-type <string>
        #train-origin-name <string>
        #train-origin-eva <short>
        #train-destination-name <strin>
        #train-destination-eva <string>

        return g