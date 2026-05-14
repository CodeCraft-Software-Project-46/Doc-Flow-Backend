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
            return Response(
                {"error": "Message is required"},
                status=400
            )

        try:
            llm = LLMService() #creates instance of LLM service and connects to Gemini AI

            # ==============================
            # STEP 0 — INTENT CHECK (NEW FIX)
            # ==============================
            intent_prompt = PromptService.is_sql_needed_prompt(user_message) #Extracts message from request
            intent = llm.generate(intent_prompt).strip().upper()

            # If NOT a data question → return directly
            if intent == "NO":
                return Response({
                    "answer": "Hi 👋 How can I help you with workflows or analytics today?",
                    "data": [],
                    "generated_sql": None
                })

            # ==============================
            # Generate SQL
            # ==============================
            sql_prompt = PromptService.generate_sql_prompt(user_message)
            generated_sql = llm.generate(sql_prompt)

            # ==============================
            # Execute SQL
            # ==============================
            results = SQLService.execute_query(generated_sql)

            # ==============================
            # Generate natural language response
            # ==============================
            response_prompt = PromptService.generate_response_prompt(
                user_message,
                results
            )

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