from django.urls import path
from .views import ChatBotView, ChatbotConfigView

urlpatterns = [
    path("chat/", ChatBotView.as_view()), #view=request handler all functionns are also views in Django
    path("config/", ChatbotConfigView.as_view()),
]        #.as_view() is a method that converts the class-based view into a function-based view that can be used in URL routing