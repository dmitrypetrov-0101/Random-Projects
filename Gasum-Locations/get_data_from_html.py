import pandas as pd
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim


def get_city(address_dict):
    # This function will try accessing "city", "town", "village" or "municipality" keys from the address information
    # provided by Nominatim. If none of such keys is found - function returns string "missing_info"
    try:
        return address_dict['city']
    except:
        try:
            return address_dict['village']
        except:
            try:
                return address_dict['town']
            except:
                try:
                    return address_dict['municipality']
                except:
                    return "Missing_info"


# Template dict with None values for each key
out_dict = {"name": None, "latitude": None, "longitude": None, "type": None, "city": None,
            "country": None, "country_code": None}

gasum = []

# Reverse geocoding function. Set limit to one request per second
locator = Nominatim(user_agent="gasumGeocoder", timeout=10)
rgeocode = RateLimiter(locator.reverse, min_delay_seconds=1)

# get HTML of the website, collect specific DIV tags which we want
url = "https://www.gasum.com/sv/hallbara-transporter/tung-trafik/tankstationer/"
r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")
mydivs = soup.find_all("div", {"class": "map-marker-link-container"})


for i in tqdm(mydivs):
    # Proccess each of the collected DIV tags, populate values into template dict, add results to output list
    i_dict = dict(out_dict)
    gasum_name = i.find('a').text
    gasum_name = gasum_name.strip()
    i_dict["name"] = gasum_name

    # guess type of location with help of icon image used by provider on website
    src = i.find('img').get('src')
    src = src.rsplit('/')[-1]
    i_dict["type"] = src

    # extract location coordinates from attributes of anchor HTML element
    gps = i.find('a').get('onclick')
    gps = gps[gps.find("(") + 2:gps.find(")") - 1]
    gps = [i for i in gps.split(',')]

    # perform reverse geocoding
    coordinates = tuple(gps)
    location = rgeocode(coordinates, language='en')
    i_dict["latitude"], i_dict["longitude"] = location.raw['lat'], location.raw['lon']
    location_data = location.raw['address']
    i_dict["city"] = get_city(location_data)
    i_dict["country"] = location_data['country']
    i_dict["country_code"] = location_data['country_code']
    gasum.append(i_dict)


gasum_df = pd.DataFrame.from_dict(gasum)
print(gasum_df.to_string())
gasum_df.to_csv(f'gasum.csv', sep=";", encoding='utf-8', index=False, header=True)
