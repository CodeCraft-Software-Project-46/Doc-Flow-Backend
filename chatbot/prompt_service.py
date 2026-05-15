from .schema import DATABASE_SCHEMA

class PromptService:

    @staticmethod
    def generate_sql_prompt(question): #intent check and SQL generation
        """Generates contextual SQL commands based on user schema."""
        return f"""
        You are a senior MySQL expert and assistant.

        {DATABASE_SCHEMA}

        USER QUESTION:
        {question}

        TASK:
        1. If the user is greeting you (hi, hello, etc) or asking a general non-data question, respond with a brief friendly greeting.
        2. If the user asks for data, analytics, or workflows, generate ONLY a valid MySQL SELECT query.

        STRICT RELATIONSHIP RULES FOR JOINS:
        - When asked 'who handles a task', 'who is assigned', or 'user responsible':
          1. Start from analytics_workflow_instance (awi)
          2. LEFT JOIN analytics_workflow (aw) ON awi.workflow_id = aw.workflow_id
          3. LEFT JOIN analytics_task_instance (ati) ON awi.instance_id = ati.workflow_instance_id
          4. LEFT JOIN analytics_role (ar) ON ati.assigned_role_id = ar.role_id
          5. LEFT JOIN analytics_user (au) ON au.role_id = ar.role_id
          This ensures you catch the user record assigned to that specific role.

        STRICT TEXT EXTRACTOR RULES:
        When extracting string values for LOWER(column) LIKE LOWER('%value%'):
        - Strip descriptive filler nouns like 'workflow', 'instance', or 'task' if they merely define object metadata.
        - Example: If user input states 'purchase order workflow', extract and use '%purchase order%'.
        - Example: If user input states 'PO approval invoice A instance', extract and use '%PO approval invoice A%'.
        - Example: If user input states 'Dept approval task', extract and use '%Dept approval%'.

        STRICT RULES FOR SQL:
        - Only generate SELECT queries.
        - No markdown formatting wrappers (Do NOT use ```sql tags), no natural text explanations.
        - ALWAYS prioritize structural LEFT JOIN statements over default INNER JOIN statements to prevent missing rows from dropping active records.
        - Use LOWER(column) LIKE LOWER('%value%') for case-insensitive partial text searching.
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
        Convert the raw data set into a highly readable, clean, human-friendly text response.

        CRITICAL TEXT FORMATTING RULES:
        1. NEVER use asterisks (**), stars, underscores (_), or markdown bold/italic tags anywhere in your text response.
        2. Present each workflow record as a distinct block, separated from other records by a full blank line break so they do not blend together.
        3. Within each record block, present the attributes using clean, indented line breaks.
        4. Write identifying labels in ALL CAPS followed by a colon to make them stand out neatly without using markdown styling (e.g., WORKFLOW:, INSTANCE NAME:, STARTED:).

        GENERAL FORMATTING RULES:
        - Use proper clean structural line breaks.
        - Present analytical list components using plain dash bullet points (- ).
        - Do NOT expose SQL string code blocks, structural keys, or raw system exceptions to the user.
        - If the dataset array is empty, strictly output: 'No matching records found'.
        - If the dataset array indicates an unexpected error flag, output: 'Unable to fetch data at the moment'.
        """