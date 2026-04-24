from rest_framework.views import APIView #A class that allows you to define API endpoints using class-based views. It provides methods for handling different HTTP methods (GET, POST, etc.) and simplifies the process of creating RESTful APIs in Django.
from rest_framework.response import Response
from rest_framework import status
from .llm_service import LLMService

class ChatBotView(APIView): #A Django class that handles API requests
    #API view A class that lets you define different HTTP methods inside one structure. 

    def post(self, request):
        message = request.data.get("message")

        prompt = f""" You are a helpful assistant.User: {message}"""            #Build prompt to send to llm

        # answer = llm.generate(prompt)

        # return Response({
        #     "answer": answer

        try:
            llm = LLMService() #Create LLM service
            answer = llm.generate(prompt)
            return Response({"answer": answer})

        except Exception as e:
            error_message = str(e)

            # Map common upstream provider failures to HTTP status codes.
            if "429" in error_message or "RESOURCE_EXHAUSTED" in error_message:
                http_status = status.HTTP_429_TOO_MANY_REQUESTS
            elif "GEMINI_API_KEY is not set" in error_message:
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            elif "401" in error_message or "403" in error_message:
                http_status = status.HTTP_502_BAD_GATEWAY
            else:
                http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

            return Response({"error": error_message}, status=http_status)
    