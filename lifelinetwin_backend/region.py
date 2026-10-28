import os

REGIONS = {
    'houston': {'name':'Houston', 'latitude':29.7075, 'longitude':-95.395},
    'heidelberg': {'name':'Heidelberg', 'latitude':49.415, 'longitude':8.6775},
}
REGION_ID = os.getenv('LIFELINETWIN_REGION','houston')
if REGION_ID not in REGIONS:
    raise ValueError('LIFELINETWIN_REGION must be houston or heidelberg')
REGION = REGIONS[REGION_ID]
