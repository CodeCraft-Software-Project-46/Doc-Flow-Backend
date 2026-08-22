from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class WorkingHoursTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/working-hours/config/save/"

    #Test 1: Valid Data
    def test_valid_config(self):
        data = {
            "work_start_time": "09:00:00",
            "work_end_time": "17:00:00",
            "work_days": [1, 2, 3, 4, 5],
            "holidays": [],
            "time_zone": "UTC",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        #❌ Test 2: Missing Fields no any data sent
    def test_missing_fields(self):
        data = {}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #no working days
    def test_no_working_days(self):
        data = {
            "work_start_time": "09:00:00",
            "work_end_time": "17:00:00",
            "work_days": [],
            "holidays": [],
            "time_zone": "UTC"
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #Missing end time
    def test_missing_end_time(self):
        data = {
            "work_start_time": "09:00:00",
            "work_days": [1],
            "holidays": [],
            "time_zone": "UTC",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        #❌ Test 3: Invalid Time
    def test_invalid_time(self):
        data = {
            "work_start_time": "abc",
            "work_end_time": "17:00:00",
            "work_days": [1],
            "holidays": [],
            "time_zone": "UTC",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        #❌ Test 4: Invalid Work Days
    def test_invalid_work_days(self):
        data = {
            "work_start_time": "09:00:00",
            "work_end_time": "17:00:00",
            "work_days": [10],
            "holidays": [],
            "time_zone": "UTC",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        #❌ Test 5: Invalid Holiday Format
    def test_invalid_holiday_format(self):
        data = {
            "work_start_time": "09:00:00",
            "work_end_time": "17:00:00",
            "work_days": [1],
            "holidays": ["01-01-2025"],
            "time_zone": "UTC",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #Same start and end time

    def test_same_start_end_time(self):
        data = {
            "work_start_time": "09:00:00",
            "work_end_time": "09:00:00",
            "work_days": [1],
            "holidays": [],
            "time_zone": "UTC"
        }

        response = self.client.post(self.url, data, format="json")

        # A start/end time that isn't a real window would let the SLA
        # engine compute a due date with zero available hours per day, and
        # calculate_due_at() raises for exactly that. The serializer now
        # rejects it up front instead.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_start_after_end_time(self):
        data = {
            "work_start_time": "17:00:00",
            "work_end_time": "09:00:00",
            "work_days": [1],
            "holidays": [],
            "time_zone": "UTC",
        }

        response = self.client.post(self.url, data, format="json")

        # Same reasoning as test_same_start_end_time, just the other way
        # the window can be invalid: start later than end.
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    #Duplicate holidays
    def test_duplicate_holidays(self):
        data = {
            "work_start_time": "09:00:00",
            "work_end_time": "17:00:00",
            "work_days": [1],
            "holidays": ["2025-01-01", "2025-01-01"],
            "time_zone": "UTC"
        }

        response = self.client.post(self.url, data, format="json")

        # backend currently allows this
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# python manage.py test working_hours