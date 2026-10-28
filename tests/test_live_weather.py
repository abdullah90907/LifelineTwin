import unittest
from unittest.mock import Mock, patch
from lifelinetwin_backend import live_weather as live


class CurrentFeedTests(unittest.TestCase):
    def setUp(self):
        live._cached = None
        live._expires = 0
        live._alerts = None
        live._alerts_expires = 0

    def response(self, payload):
        result=Mock()
        result.json.return_value=payload
        return result

    @patch.object(live.requests,'get')
    def test_current_weather_is_cached_and_requests_selected_location(self, get):
        get.return_value=self.response({'current':{'time':'2026-10-29T00:00'},'hourly':{'time':['2026-10-29T00:00']},
                                        'latitude':29.7,'longitude':-95.4,'current_units':{},'hourly_units':{}})
        first=live.current_weather()
        self.assertEqual(first,live.current_weather())
        self.assertEqual(get.call_count,1)
        self.assertEqual(get.call_args.kwargs['params']['latitude'],live.REGION['latitude'])

    @patch.object(live.requests,'get')
    def test_missing_current_data_is_not_accepted(self,get):
        get.return_value=self.response({'current':{},'hourly':{}})
        with self.assertRaises(ValueError):
            live.current_weather()
        self.assertIsNone(live._cached)

    @patch.object(live.requests,'get')
    def test_empty_official_alert_response_remains_empty(self,get):
        get.return_value=self.response({'features':[]})
        self.assertEqual(live.active_alerts()['alerts'],[])
        self.assertEqual(live.active_alerts()['alerts'],[])
        self.assertEqual(get.call_count,1)

    @patch.object(live.requests,'get',side_effect=TimeoutError('provider timeout'))
    def test_expired_weather_is_not_substituted_for_failed_refresh(self,get):
        live._cached={'old':'historical data'}
        with self.assertRaises(TimeoutError):
            live.current_weather()


if __name__=='__main__':
    unittest.main()
