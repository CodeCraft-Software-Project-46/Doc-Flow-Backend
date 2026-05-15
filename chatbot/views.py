from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .llm_service import LLMService
from .prompt_service import PromptService
from .sql_service import SQLService

class ChatBotView(APIView):

    def post(self, request):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Message is required"},status=400)

        try:
            llm = LLMService() #creates instance of LLM service and connects to Gemini AI

            # STEP 1: Combined Intent + SQL Generation (Saves 1 API Call)
            # We use a combined prompt to ask: "Give me SQL or a Greeting"
            system_prompt = PromptService.generate_sql_prompt(user_message)
            llm_response = llm.generate(system_prompt).strip()

            # Check if the LLM sent a greeting/fallback instead of SQL
            if not llm_response.upper().startswith("SELECT"):
                return Response({
                    "answer": llm_response,
                    "data": [],
                    "generated_sql": None
                })

            generated_sql = llm_response

            # STEP 2: Execute SQL
            results = SQLService.execute_query(generated_sql)

            # STEP 3: Generate natural language response
            response_prompt = PromptService.generate_response_prompt(user_message, results)
            final_answer = llm.generate(response_prompt)

            return Response({
                "answer": final_answer,
                "data": results,
                "generated_sql": generated_sql
            })

        except Exception as e:
            print("Backend Error:", e)

            return Response({
                "question": user_message,
                "answer": "Sorry, I couldn’t process your request right now."
            }, status=status.HTTP_200_OK)