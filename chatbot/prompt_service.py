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
Generate ONLY a valid MySQL SELECT query.

STRICT RULES:
- Only SELECT queries
- No markdown
- No explanations
- Use LOWER(column) LIKE LOWER('%value%') for text search
"""

    @staticmethod
    def generate_response_prompt(question, data):

        return f"""
    You are a professional analytics assistant.

    QUESTION:
    {question}

    DATA:
    {data}

    TASK:
    Convert the data into a clean human-readable response.

    FORMATTING RULES:
    - Use proper line breaks
    - Use bullet points (-) for lists
    - Add a heading sentence if it is a list (example: "The following tasks breached their SLA:")
    - Do NOT use markdown symbols like ** or ###
    - Do NOT show raw SQL or errors
    - Keep response easy to read and structured

    IF DATA IS A LIST:
    - Each item MUST be on a new line with "- "

    IF EMPTY:
    - Say: "No matching records found"

    IF ERROR:
    - Say: "Unable to fetch data at the moment"
"""