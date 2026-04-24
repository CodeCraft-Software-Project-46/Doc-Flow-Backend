from django.urls import path
from .views import ChatBotView

urlpatterns = [
    path("chat/", ChatBotView.as_view()), #view=request handler all functionns are also views in Django
]        #.as_view() is a method that converts the class-based view into a function-based view that can be used in URL routing