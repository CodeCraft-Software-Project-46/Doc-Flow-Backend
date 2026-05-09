from .schema import DATABASE_SCHEMA


class PromptService:

    @staticmethod
    def generate_sql_prompt(question):

        return f"""
You are a senior MySQL expert.

{DATABASE_SCHEMA}

USER QUESTION:
{question}

TASK:
1. Understand the user intent
2. Identify correct tables
3. Build proper JOINs
4. Generate optimized MySQL SELECT query

IMPORTANT MATCHING RULES:
- Use LOWER(column) LIKE LOWER('%value%')
  for text comparisons
- Avoid exact = matching for names
- Use flexible partial matching

STRICT RULES:
- Return ONLY SQL
- No markdown
- No explanations
- No comments
- ONLY SELECT queries
"""

    @staticmethod
    def generate_response_prompt(question, data):

        return f"""
You are a helpful analytics AI assistant.

USER QUESTION:
{question}

DATABASE RESULTS:
{data}

TASK:
Generate a natural natural-language response.

RULES:
- Be concise
- Be human readable
- If no data exists, clearly say no matching data was found
"""