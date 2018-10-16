import requests

from cloudbot import hook

api_url_metar = "http://api.av-wx.com/metar/"
api_url_taf = "http://api.av-wx.com/taf/"


@hook.command()
def metar(text):
    """[ICAO station code] - returns the metars information for the specified station. A list of station codes can be found here: http://weather.rap.ucar.edu/surface/stations.txt"""
    station = text.split(' ')[0].upper()
    if not len(station) is 4:
        return "please specify a valid station code see http://weather.rap.ucar.edu/surface/stations.txt for a list."

    request = requests.get(api_url_metar + station)
    request.raise_for_status()
    r = request.json()['reports'][0]
    out = r['name'] + ": " + r['raw_text']
    return out


@hook.command()
def taf(text):
    """[ICAO station code] - returns the taf information for the specified station. A list of station codes can be found here: http://weather.rap.ucar.edu/surface/stations.txt"""
    station = text.split(' ')[0].upper()
    if not len(station) is 4:
        return "please specify a valid station code see http://weather.rap.ucar.edu/surface/stations.txt for a list."

    request = requests.get(api_url_taf + station)
    request.raise_for_status()
    r = request.json()['reports'][0]
    out = r['name'] + ": " + r['raw_text']
    return out
