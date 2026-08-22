from django.apps import apps
from django.test import TestCase


class ChatbotModuleSmokeTests(TestCase):
	def test_chatbot_app_is_registered(self):
		self.assertTrue(apps.is_installed("chatbot"))
