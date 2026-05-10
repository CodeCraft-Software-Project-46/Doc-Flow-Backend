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

            # STEP 1 — Generate SQL
            sql_prompt = PromptService.generate_sql_prompt(
                user_message
            )

            generated_sql = llm.generate(sql_prompt)

            # STEP 2 — Execute SQL
            results = SQLService.execute_query(
                generated_sql
            )

            # STEP 3 — Generate response
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
            print("Backend Error:", e)  # log only

            return Response(
                {
                    "question": user_message,
                    "answer": "Sorry, I couldn’t process your request right now. Please try again later."
                },
                status=status.HTTP_200_OK
            )