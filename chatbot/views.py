from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from . import embedding_service, kpi_router
from .llm.factory import PROVIDER_NAMES
from .llm.ollama_provider import OllamaUnavailableError
from .llm_service import LLMService
from .models import ChatbotConfig
from .prompt_service import PromptService
from .sql_service import SQLService


class ChatbotConfigView(APIView):
    """Lets the frontend initialize its provider switch against the
    admin-configured default (chatbot/models.py::ChatbotConfig)."""

    def get(self, request):
        config = ChatbotConfig.current()
        return Response({
            "active_provider": config.active_provider,
            "available_providers": list(PROVIDER_NAMES),
        })


class ChatBotView(APIView):

    def post(self, request):
        user_message = request.data.get("message")
        if not user_message:
            return Response({"error": "Message is required"}, status=400)

        # Optional per-message provider override (e.g. "gemini" or "ollama");
        # falls back to ChatbotConfig.current().active_provider if omitted
        # or invalid. See LLMService in llm_service.py.
        provider_override = request.data.get("provider")

        try:
            llm = LLMService(provider_override=provider_override) #creates instance of LLM service, resolves active provider (Gemini/Ollama)

            # STEP 0: Try routing straight to an existing KPI/chart calculation.
            # Chart data is never stored, so reuse the exact same widget
            # functions analytics already uses (see chatbot/kpi_router.py)
            # instead of asking the LLM to hand-write aggregate SQL.
            kpi_result = kpi_router.route(user_message)
            if kpi_result is not None:
                response_prompt = PromptService.generate_response_prompt(user_message, kpi_result)
                final_answer = llm.generate(response_prompt)
                return Response({
                    "answer": final_answer,
                    "data": kpi_result,
                    "generated_sql": None
                })

            # STEP 1: Combined Intent + SQL Generation
            # Generate a combined prompt to ask: "Give me SQL or a Greeting"
            system_prompt = PromptService.generate_sql_prompt(user_message)
            llm_response = llm.generate(system_prompt).strip()

            # Not every model follows "output ONLY raw SQL" as strictly as
            # Gemini does (local models especially tend to wrap the query in
            # chat/markdown) so pull the SELECT out of the response rather
            # than requiring it to be the very first characters.
            generated_sql = SQLService.extract_sql_statement(llm_response)

            # No SELECT found at all. Rather than trusting the model's raw
            # free-form answer outright (it may just be a greeting, but it
            # could also be a descriptive question it couldn't turn into
            # SQL), see if the RAG index has anything relevant -- retrieve()
            # only returns snippets above a similarity threshold, so this is
            # a no-op for genuine greetings and only kicks in for questions
            # actually related to indexed workflow/document/instance content.
            if not generated_sql:
                context_snippets = embedding_service.retrieve(user_message, top_n=5)
                if context_snippets:
                    response_prompt = PromptService.generate_response_prompt(user_message, [], context_snippets)
                    final_answer = llm.generate(response_prompt)
                    return Response({"answer": final_answer, "data": [], "generated_sql": None})

                return Response({
                    "answer": llm_response,
                    "data": [],
                    "generated_sql": None
                })

            # STEP 2: Execute SQL. A weaker model can hallucinate an invalid
            # query (wrong column/table name); rather than let that raise
            # all the way out to the generic "Sorry" fallback below, treat
            # it the same as an empty result and fall back to RAG retrieval.
            try:
                results = SQLService.execute_query(generated_sql) #send to SQL service execute_query method to clean, validate, and run the SQL against DB and return results
            except Exception as sql_error:
                print("SQL execution failed, falling back to RAG:", sql_error)
                results = []

            # STEP 2b: If the SQL came back empty (or failed to execute),
            # fall back to RAG retrieval over indexed workflow/document/
            # instance text so descriptive questions still get a useful
            # answer instead of "no records".
            context_snippets = []
            if not results:
                context_snippets = embedding_service.retrieve(user_message, top_n=5)

            # STEP 3: Generate natural language response
            response_prompt = PromptService.generate_response_prompt(user_message, results, context_snippets) # send to prompt service to convert data into human readable response
            final_answer = llm.generate(response_prompt)#generate response

            return Response({
                "answer": final_answer,
                "data": results,
                "generated_sql": generated_sql
            })

        except OllamaUnavailableError as e:
            print("Backend Error:", e)

            return Response({
                "question": user_message,
                "answer": "The local Ollama model isn't reachable right now. Make sure Ollama is running on this machine, then try again -- or switch the provider to Gemini."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print("Backend Error:", e)

            return Response({
                "question": user_message,
                "answer": "Sorry, I couldn’t process your request right now."
            }, status=status.HTTP_200_OK)
