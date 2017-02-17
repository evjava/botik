import json

from time import sleep
from urllib import request
from my_token import key

seconds_between_attempts = 3

def load(url):
    try:
        raw_json = request.urlopen(url).read().decode()
        sleep(seconds_between_attempts)
        return json.loads(raw_json)
    except BaseException:
        return None


def get_estimate(json_data):
    if json_data is None:
        return None
    try:
        routes = json_data['routes']
        traffic_times = []
        for route in routes:
            if route['type'] == 'auto':
                props = route['properties']
                tt = props['timeWithTraffic']['value']
                traffic_times.append(tt)
        return min(traffic_times)
    except BaseException:
        return None


def get_expected_time(point_from, point_to):
    rest_query = url_template.format(loc_from=point_from, loc_to=point_to, apikey=key)
    json_answer = load(rest_query)
    estimate = get_estimate(json_answer)
    return estimate


url_template = 'https://router.api-maps.yandex.ru/v1/?points={loc_from}~{loc_to}&type=auto&apikey={apikey}'

# todo hide key
