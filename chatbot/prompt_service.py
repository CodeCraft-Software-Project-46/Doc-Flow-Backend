from .schema import DATABASE_SCHEMA

class PromptService:

    @staticmethod
    def is_sql_needed_prompt(question): #checking whether the question is related to data and requires SQL or not
        return f"""
        You are a classifier for a chatbot system.

        Decide if the user question needs a SQL database query.

        RULES:
        - If user is greeting (hi, hello, hey, good morning), return NO
        - If user is casual conversation, return NO
        - If user is asking for data, analytics, workflows, tasks, documents, return YES

        OUTPUT ONLY:
        YES or NO

        QUESTION:
        {question}
        """

    @staticmethod
    def generate_sql_prompt(question): #Convert user question → SQL query

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
    def generate_response_prompt(question, data): #Convert data → human-readable response

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
        - Use bullet points (-)
        - Do NOT show SQL or errors
        - If list → each item on new line
        - If empty → "No matching records found"
        - If error → "Unable to fetch data at the moment"
        """