# chatbot/schema.py

DATABASE_SCHEMA = """

YOU ARE WORKING WITH AN ANALYTICS WORKFLOW SYSTEM.

ALL TABLES START WITH PREFIX: analytics_

==================================================
CORE TABLES
==================================================

1. analytics_workflow
- workflow_id (PRIMARY KEY)
- name
- definition (JSON describing workflow task order and structure)
- created_at

--------------------------------------------------

2. analytics_workflow_instance
- instance_id (PRIMARY KEY)
- workflow_id (FOREIGN KEY → analytics_workflow.workflow_id)
- document_id (FOREIGN KEY → analytics_document.document_id)
- status (running, completed, cancelled)
- created_at
- completed_at
- instance_name

--------------------------------------------------

3. analytics_task_instance
- task_id (PRIMARY KEY)
- task_name
- workflow_instance_id (FOREIGN KEY → analytics_workflow_instance.instance_id)
- assigned_role_id (FOREIGN KEY → analytics_role.role_id)
- status (pending, running, completed)
- created_at
- due_at
- completed_at
- sla_hours
- sla_status (pending, met, breached)

==================================================
SUPPORT TABLES
==================================================

4. analytics_document
- document_id (PRIMARY KEY)
- document_name

--------------------------------------------------

5. analytics_role
- role_id (PRIMARY KEY)
- role_name

--------------------------------------------------

6. analytics_department
- department_id (PRIMARY KEY)
- department_name

--------------------------------------------------

7. analytics_user
- user_id (PRIMARY KEY)
- user_name
- department_id (FOREIGN KEY → analytics_department.department_id)
- role_id (FOREIGN KEY → analytics_role.role_id)

==================================================
RELATIONSHIPS
==================================================

WORKFLOW RELATIONSHIPS:
- analytics_workflow_instance.workflow_id → analytics_workflow.workflow_id
- analytics_workflow_instance.document_id → analytics_document.document_id

TASK RELATIONSHIPS:
- analytics_task_instance.workflow_instance_id → analytics_workflow_instance.instance_id
- analytics_task_instance.assigned_role_id → analytics_role.role_id

USER RELATIONSHIPS:
- analytics_user.role_id → analytics_role.role_id
- analytics_user.department_id → analytics_department.department_id

==================================================
IMPORTANT BUSINESS LOGIC
==================================================

- A workflow defines a process template.
- A workflow instance is a running execution of a workflow.
- A task instance is a real task execution inside a workflow instance.

- Tasks are assigned to ROLES, not directly to users.
- Users belong to roles through analytics_user.role_id.
- Multiple users can belong to the same role.

- SLA status meanings:
    - met → completed within SLA
    - breached → exceeded SLA time
    - pending → task not completed yet

==================================================
IMPORTANT QUERY GENERATION RULES
==================================================

- ALWAYS use analytics_ prefixed tables
- Generate ONLY SELECT queries
- NEVER generate DELETE, DROP, UPDATE, INSERT, ALTER, or TRUNCATE queries
- Prefer JOINs using foreign key relationships
- Use LIKE for flexible text matching when appropriate
- Use analytics_task_instance for task-level analytics
- Use analytics_workflow_instance for workflow execution analytics
- Use analytics_workflow for workflow definitions only

==================================================
SPECIAL QUERY RULES
==================================================

- If user asks:
    "who is assigned"
    "who is assignee"
    "who handles task"

THEN:
- JOIN analytics_task_instance
- JOIN analytics_role
- JOIN analytics_user

through:
analytics_task_instance.assigned_role_id
→ analytics_role.role_id
→ analytics_user.role_id

==================================================
TEXT MATCHING RULES
==================================================

- For text searching, prefer:
    LOWER(column_name) LIKE LOWER('%value%')

instead of:
    column_name = 'value'

- This is important for:
    task names
    workflow names
    instance names
    document names
    user names

- Use flexible partial matching whenever possible.

EXAMPLES:

GOOD:
LOWER(ati.task_name) LIKE LOWER('%Dept Approval%')

GOOD:
LOWER(awi.instance_name) LIKE LOWER('%Invoice A%')

BAD:
ati.task_name = 'Dept Approval task'

==================================================
STRICT TEXT MATCHING RULE
==================================================

ALWAYS use:

LOWER(column_name) LIKE LOWER('%value%')

NEVER use:
=
for text comparisons.

ALL text searching MUST be case-insensitive.

"""