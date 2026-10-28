"""Bounded current-weather retrieval; no inferred road closures."""
from datetime import datetime, timezone
from threading import Lock
import time

import requests
from .region import REGION

_lock = Lock()
_alert_lock = Lock()
_cached = None
_expires = 0.0
_alerts = None
_alerts_expires = 0.0


def current_weather():
    global _cached, _expires
    with _lock:
        if _cached is not None and time.monotonic() < _expires:
            return _cached
        response = requests.get('https://api.open-meteo.com/v1/forecast', params={
            'latitude': REGION['latitude'], 'longitude': REGION['longitude'], 'timezone': 'GMT',
            'current': 'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code',
            'hourly': 'temperature_2m,precipitation_probability,precipitation,wind_speed_10m',
            'forecast_days': 2,
        }, timeout=(5, 20))
        response.raise_for_status()
        payload = response.json()
        if not payload.get('current', {}).get('time') or not payload.get('hourly', {}).get('time'):
            raise ValueError('Weather provider returned incomplete current conditions')
        _cached = {
            'source': 'Open-Meteo', 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'location': REGION['name'], 'latitude': payload['latitude'], 'longitude': payload['longitude'],
            'current': payload['current'], 'current_units': payload['current_units'],
            'hourly': payload['hourly'], 'hourly_units': payload['hourly_units'],
            'cache_seconds': 300,
            'limitations': 'Model-derived current conditions and forecasts; not station observations, traffic, or verified road closures.',
        }
        _expires = time.monotonic() + 300
        return _cached


def active_alerts():
    global _alerts, _alerts_expires
    with _alert_lock:
        if _alerts is not None and time.monotonic() < _alerts_expires:
            return _alerts
        response=requests.get('https://api.weather.gov/alerts/active',params={
            'point':f"{REGION['latitude']},{REGION['longitude']}",
        },headers={'User-Agent':'LifelineTwin (https://github.com/abdullah90907/LifelineTwin)',
                   'Accept':'application/geo+json'},timeout=(5,20))
        response.raise_for_status()
        data=response.json()
        if not isinstance(data.get('features'),list):
            raise ValueError('Incomplete NWS alert response')
        _alerts={'source':'National Weather Service','retrieved_at':datetime.now(timezone.utc).isoformat(),
                 'location':REGION['name'],'alerts':[
                     {key:feature.get('properties',{}).get(key) for key in
                      ('id','event','severity','headline','description','instruction','onset','expires','areaDesc')}
                     for feature in data['features']
                 ]}
        _alerts_expires=time.monotonic()+300
        return _alerts
