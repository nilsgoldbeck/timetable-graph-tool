#%%
import requests

#%%
def GetStations(category_string):

  url = "https://api.deutschebahn.com/stada/v2/stations"

  headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer 635730573e4f824efa4cd50b81cb0e33',
  }

  data = {'category': category_string}

  response = requests.get(url, data, headers=headers)

  return response.json()['result']


#%%
def GetDepartures(eva_number):
  
  url = "https://api.deutschebahn.com/fahrplan-plus/v1/departureBoard/" + str(eva_number)

  headers = {
  'Accept': 'application/json',
  'Authorization': 'Bearer 635730573e4f824efa4cd50b81cb0e33',
  }

  data = {'date': '2019-06-11'}

  response = requests.get(url, data, headers=headers)

  return response.json()

#%%
stations = GetStations('1-3')

#%%
print(len(stations))
for station in response.json()['result']:
  print(station['name'])
  print(station['evaNumbers'][-1]['number'])


#%%
departures = GetDepartures(8000002)

#%%
for departure in departures:
  print(departure['name'])
  print(departure['dateTime'])
  print(departure['detailsId'])

#%%




