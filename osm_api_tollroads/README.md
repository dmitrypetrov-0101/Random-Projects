## Description
This project explores an option to use API provided by OpenStreetMap for detecting route points that belong to the 
road, where toll needs to be paid for travelling.

## Approach
API provided by OpenStreetMap allows getting different kinds of information about locations on the map. The interest of this 
project is finding out if specific point of the vehicle route belongs to motorway, where toll must be paid by 
vehicle-owners.

OSM database provides such information using `toll` key https://wiki.openstreetmap.org/wiki/Key:toll.
We can use this to get a list of `way` objects in OSM database, where `toll` key is set to `yes`.

OSM developed Overpass QL language to make api calls.
For instance, request such as this will return all objects inside the bounding box, where properties of way-objects 
are set to have `toll='yes'`
```
[out:json][timeout:25];
(
  way["toll"="yes"](49.10265, 0.99976, 51.60778, 5.34485);
);
(._;>;);
out;
```

This query can be tested here http://overpass-turbo.eu/

The response for such query will return a list of `way` objects matching the query conditions, together with the list 
of individual `nodes` that have any relation to the `way`. `nodes` only hold Latitude and Longitude information. 
`ways` hold details that we need to investigate (an object being a motorway, toll property set to 'yes').

One of the challenges is that motorways are not the only `way` objects in the database, which can have active `toll` 
property. Other object could be: ferry routes, boat ride routes along rivers, etc. We need to be certain that `way` 
in the response is in fact a motorway, and then find the closest node related to that motorway.  

## Process

Handling of the task is implemented in Python file [toll_route_checker.py](toll_route_checker.py)
This program collects route points from .gpx file, which presents information in an xml way. 
Then, program makes a call to OSM api about toll objects inside specific radius for each point of the route. Point 
coordinates together with 'around' filter are passed into api query.
https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Relative_to_other_elements_.28around.29

After receiving the response from the API, the program calculates the distance in meters to each node related to the 
way. This is performed with the help of GeoPy module https://geopy.readthedocs.io/en/stable/#module-geopy.distance.
If the closest node is located, details of the route point are updated with relevant information, and a `toll` key for 
the point of the route is set to 'yes'. In case api response returns empty list, the `toll` key for the route point is 
set to 'no'. In case there was any error during receiving of the information, the `toll` key is set to `no data`.

The output of the program is two csv files: one with details of each point of the route, the other with estimation of 
how much time it took to get the response from API and process it for each point.

## Source of test data

As a source for data, this project uses details of the route between French cities of Calais and Lille.
http://map.project-osrm.org/?z=10&center=50.781629%2C2.572174&loc=50.948800%2C1.874680&loc=50.636565%2C3.063528&hl=en&alt=1&srv=0

One of the buttons at the bottom of the page provides route points in .gpx file

## Results and analysis

The output files are analyzed in 
[OSM_results.ipynb notebook](OSM_results.ipynb).

Some of the interactive features of Jupyter are disabled here. So an alternative link to view the notebook is available 
here https://nbviewer.jupyter.org/github/dmitrypetrov-0101/Random-Projects/blob/main/osm_api_tollroads/OSM_results.ipynb

## Conclusions

The current approach of making a separate api call for each point of the route is extremely time-consuming and 
inefficient - it took over 40 minutes to handle 2385 points of a 117-kilometer journey from the test dataset. On average, it took slightly over a 
second to process each point. 

For any serious business scenario with dozens of vehicles involved another approach is needed. Perhaps passing 
coordinates of a batch of points into api, instead of making call for each of the route point individually. 



