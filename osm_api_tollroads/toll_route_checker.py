import xml.etree.ElementTree as et
from urllib.request import urlopen
from geopy.distance import geodesic
import requests
import time
import pandas as pd


def get_osm_data(coordinates):
    """
    This function makes an API call to OverPass endpoint to get ways in OSM database that have a tag "toll" set to "yes"
     inside a specified radius around coordinates passed as a parameter
    :param coordinates: string with GPS coordinates. The expected response by OSM api holds objects within the radius of
    these coordinates
    :return: HTTP status by OSM API, headers of OSM API response, body of OSM API response
    """

    # main endpoint. safe 10000 calls per day
    osm_endpoint1 = 'https://overpass-api.de/api/interpreter'
    # additional endpoint. unlimited calls, but much slower
    osm_endpoint2 = 'https://overpass.kumi.systems/api/interpreter'
    radius = 5

    osm_endpoint = osm_endpoint1

    api_query = """
    [out:json][timeout:25];
    (way["toll"="yes"](around:{rad},{coord}););
    (._;>;);
    out;
    """.format(rad=radius, coord=coordinates)

    # call API. Handle possible exceptions
    try:
        r = requests.get(osm_endpoint, params={'data': api_query}, timeout=25)
        r.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        kill_url = 'http://overpass-api.de/api/kill_my_queries'
        urlopen(kill_url)
        resp = 'error'
        data = str(errh)
        headers = {}
        return resp, headers, data
    except requests.exceptions.ConnectionError as errc:
        kill_url = 'http://overpass-api.de/api/kill_my_queries'
        urlopen(kill_url)
        resp = 'error'
        data = str(errc)
        headers = {}
        return resp, headers, data
    except requests.exceptions.Timeout as errt:
        kill_url = 'http://overpass-api.de/api/kill_my_queries'
        urlopen(kill_url)
        resp = 'error'
        data = str(errt)
        headers = {}
        return resp, headers, data
    except requests.exceptions.RequestException as err:
        kill_url = 'http://overpass-api.de/api/kill_my_queries'
        urlopen(kill_url)
        resp = 'error'
        data = str(err)
        headers = {}
        return resp, headers, data

    # Return API response
    if r.status_code == 200:
        # OK status code
        headers = r.headers
        resp = r.status_code
        data = r.json()
        return resp, headers, data
    elif r.status_code == 429:
        # too many requests from this IP
        kill_url = 'http://overpass-api.de/api/kill_my_queries'
        urlopen(kill_url)
        r = requests.get(osm_endpoint, params={'data': api_query})
        headers = r.headers
        resp = r.status_code
        data = r.json()
        print('error 429', kill_url)
        return resp, headers, data
    elif r.status_code == 504:
        # time-out status code. try another endpoint
        osm_endpoint = osm_endpoint2
        r = requests.get(osm_endpoint, params={'data': api_query})
        if r.status_code != 200:
            headers = r.headers
            resp = r.status_code
            data = r.json()
            return resp, headers, data
        headers = r.headers
        resp = r.status_code
        data = r.json()
        return resp, headers, data
    elif r.status_code == 400:
        # Bad Request status code. Error in API request syntax
        resp = r.status_code
        headers = {}
        data = {}
        return resp, headers, data
    else:
        headers = r.headers
        resp = r.status_code
        data = r.json()
        print('other response code', resp, data)
        return resp, headers, data


def handle_osm_response(status, data, pcoord):
    """
    This function loops through OSM response, to find the node, which is closest to coordinates of the route point.
    If the list of elements in OSM response is empty - then return is that no toll roads are found
    :param status: HTTP status response for OSM call
    :param data: JSON body of the OSM response
    :param pcoord: coordinates of the point in the route
    :return: dictionary with OSM information about closest node, and the way to which this node is related to
    """

    return_fields = {'osmWayID': None, 'osmWayType': None, 'int_ref': None, 'ref': None, 'way_name': None,
                     'operator': None, 'toll': None, 'nodeId': None, 'nodeLat': None, 'nodeLon': None,
                     'p2nodeDistance': None, 'comments': None}
    collector = {'osmWayID': None, 'osmWayType': None, 'int_ref': None, 'ref': None, 'way_name': None,
                 'operator': None, 'toll': None, 'nodeId': None, 'nodeLat': None, 'nodeLon': None,
                 'p2nodeDistance': None, 'comments': None}
    way_types_to_consider = ['motorway', 'motorway_link']
    related_nodes = []
    if not isinstance(data, dict):
        if data is None:
            data = 'data returned is None'
        return_fields.update({'toll': 'No data', 'comments': status + ', ' + str(data)})
        return return_fields

    elif status == 200:
        if 'elements' not in data.keys():
            return_fields.update({'toll': 'No data', 'comments': status + ', ' + data})
            return return_fields
        elif len(data['elements']) == 0:
            # no results in OSM response -> no toll roads around
            return_fields.update({'toll': 'No', 'comments': 'No toll objects found'})
            return return_fields
        dist = None
        for element in data['elements']:
            if element['type'] == 'way':
                if element['tags']['highway'] not in way_types_to_consider:
                    collector.update({'osmWayID': element['id'], 'osmWayType': element['tags'].get('highway', 'na'),
                                      'int_ref': element['tags'].get('int_ref', 'na'),
                                      'ref': element['tags'].get('ref', 'na'),
                                      'way_name': element['tags'].get('name', 'na'),
                                      'operator': element['tags'].get('operator', 'na'),
                                      'toll': element['tags']['toll']})
                    continue
                related_nodes = element['nodes']
                # loop nodes which have relation to the way with "toll=yes" tag
                for node in related_nodes:
                    # find node details in OSM response JSON
                    for new_element in data['elements']:
                        if new_element['id'] == node:
                            lat = new_element['lat']
                            lon = new_element['lon']
                            coordinates = list((lat, lon))
                            new_dist = abs(int(geodesic(coordinates, pcoord).m))
                            node_info = (node, lat, lon, new_dist)
                            if dist is None:
                                dist = node_info[3]
                                collector.update({'osmWayID': element['id'],
                                                  'osmWayType': element['tags'].get('highway', 'na'),
                                                  'int_ref': element['tags'].get('int_ref', 'na'),
                                                  'ref': element['tags'].get('ref', 'na'),
                                                  'way_name': element['tags'].get('name', 'na'),
                                                  'operator': element['tags'].get('operator', 'na'),
                                                  'toll': element['tags']['toll'], 'nodeId': node_info[0],
                                                  'nodeLat': node_info[1],
                                                  'nodeLon': node_info[2], 'p2nodeDistance': node_info[3]})
                                break
                            elif node_info[3] > dist:
                                break
                            elif node_info[3] < dist:
                                dist = node_info[3]
                                collector.update({'osmWayID': element['id'],
                                                  'osmWayType': element['tags'].get('highway', 'na'),
                                                  'int_ref': element['tags'].get('int_ref', 'na'),
                                                  'ref': element['tags'].get('ref', 'na'),
                                                  'way_name': element['tags'].get('name', 'na'),
                                                  'operator': element['tags'].get('operator', 'na'),
                                                  'toll': element['tags']['toll'], 'nodeId': node_info[0],
                                                  'nodeLat': node_info[1],
                                                  'nodeLon': node_info[2], 'p2nodeDistance': node_info[3]})
                                break
                            elif -1 < dist < 1:
                                break
        return_fields.update(collector)
        return return_fields
    else:
        return_fields.update({'toll': 'No data', 'comments': status + ', ' + data})
        return return_fields


program_start = time.time()
# read gpx/xml file with route info, and add points of the route into a list
tree = et.parse('calais_lille.gpx')
root = tree.getroot()
nmsps = {'ns': 'http://www.topografix.com/GPX/1/1'}
points = root.findall('*/ns:trkseg/ns:trkpt', nmsps)

# Put route points from gpx/xml file into dictionary. Order number of the point is the key.
point_dict = {}
stats = []
counter = 0
for i in points:
    counter += 1
    lat = i.get('lat')
    lon = i.get('lon')
    point_dict[counter] = {'pointID': counter, 'pointLat': lat, 'pointLon': lon}

print('Count of route points: ', len(point_dict))

# read dict with points, perform calculations and API calls for each point
for i in point_dict:
    rowstart = time.time()
    coord1 = list((point_dict[i]['pointLat'], point_dict[i]['pointLon']))
    try:
        coord2 = list((point_dict[i-1]['pointLat'], point_dict[i-1]['pointLon']))
    except KeyError:
        coord2 = coord1
    meters = int(geodesic(coord1, coord2).m)
    point_dict[i].update({'p2p_dist': meters})
    call_coordinates = f'{point_dict[i]["pointLat"]}, {point_dict[i]["pointLon"]}'
    response_code, headers, data = get_osm_data(call_coordinates)
    data_dict = handle_osm_response(status=response_code, data=data, pcoord=call_coordinates)
    point_dict[i].update(data_dict)
    rowend = time.time()
    rowduration = rowend - rowstart
    print(response_code, i, f'{rowduration:.2f} sec.')
    stats.append({'row': i, 'response_code': response_code, 'duration': rowduration})

program_end = time.time()
duration = program_end - program_start
print(point_dict)
print(f'Runtime duration: {duration:.2f}')

all_points = pd.DataFrame.from_dict(point_dict).T
all_stats = pd.DataFrame(stats)

all_points.to_csv("route_points.csv", sep=';', encoding='utf-8', index=False)
all_stats.to_csv("execution_stats.csv", sep=';', encoding='utf-8', index=False)

