# chatbot/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .llm_service import LLMService
from .prompt_service import PromptService
from .sql_service import SQLService


class ChatBotView(APIView):

    def post(self, request):

        try:

            user_message = request.data.get("message")

            if not user_message:
                return Response(
                    {"error": "Message is required"},
                    status=400
                )

            llm = LLMService()

            # STEP 1 — Generate SQL Query
            sql_prompt = PromptService.generate_sql_prompt(
                user_message
            )

            generated_sql = llm.generate(sql_prompt)

            # STEP 2 — Execute SQL
            results = SQLService.execute_query(
                generated_sql
            )

            # STEP 3 — Generate Natural Response
            response_prompt = PromptService.generate_response_prompt(
                user_message,
                results
            )

            final_answer = llm.generate(response_prompt)

            return Response({
                "question": user_message,
                "generated_sql": generated_sql,
                "data": results,
                "answer": final_answer
            })

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )