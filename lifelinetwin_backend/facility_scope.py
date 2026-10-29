"""Documented emergency-care scope; no live capacity/availability assertion."""
REVIEWED_ON='2026-10-29'
SOURCES={
 'houston':{
  'Ben Taub General Hospital':'https://www.harrishealth.org/locations-hh/Pages/ben-taub.aspx',
  'Houston Methodist Hospital':'https://www.houstonmethodist.org/locations/texas-medical-center/emergency-department/',
 },
 'alabama':{
  'DCH Regional Medical Center':'https://www.dchsystem.com/services/emergency-services/',
  'Northport Medical Center':'https://www.dchsystem.com/services/emergency-services/',
 },
}

def eligible_facilities(region,records):
    return [{**f,'capability_status':'Emergency services documented; live availability and capacity unverified',
             'service_source':SOURCES[region][f['name']],'service_reviewed_on':REVIEWED_ON}
            for f in records if f['name'] in SOURCES[region]]
