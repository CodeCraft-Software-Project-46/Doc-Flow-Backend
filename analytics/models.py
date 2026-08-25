from django.db import models

class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "analytics_department"

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "analytics_role"

class User(models.Model):
    user_id = models.AutoField(primary_key=True)

    user_name = models.CharField(max_length=255)

    department = models.ForeignKey(
        Department,
        on_delete=models.DO_NOTHING,
        db_column="department_id",
        related_name="users"
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.DO_NOTHING,
        db_column="role_id",
        related_name="users"
    )

    class Meta:
        managed = False
        db_table = "analytics_user"    #Django will NOT create or modify tables we're using an existing database just reading existing tables... 

class Document(models.Model):
    document_id = models.AutoField(primary_key=True)
    document_name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "analytics_document"

class Workflow(models.Model):
    workflow_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    definition = models.TextField()

    class Meta:
        managed = False
        db_table = "analytics_workflow"

class WorkflowInstance(models.Model):
    instance_id = models.AutoField(primary_key=True)

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.DO_NOTHING,
        db_column="workflow_id",
        related_name="instances"
    )

    instance_name = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    document_id = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=50)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "analytics_workflow_instance"


class BottleneckScoreWeights(models.Model):
    """
    Singleton config row (same pattern as working_hours.WorkingHoursConfig)
    holding the weights used to blend a workflow's average completion time,
    SLA breach percentage and task volume into its bottleneck score. Kept
    as an owned/managed table (unlike the reporting models above) since it
    is analytics' own setting, not data read from another service.
    """

    time_weight = models.FloatField(default=0.45)
    breach_weight = models.FloatField(default=0.45)
    volume_weight = models.FloatField(default=0.10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_bottleneck_score_weights"

    def __str__(self):
        return (
            f"Bottleneck weights (time={self.time_weight}, "
            f"breach={self.breach_weight}, volume={self.volume_weight})"
        )

    @classmethod
    def current(cls):
        """Latest configured weights, or the 0.45/0.45/0.10 default if none has been saved yet."""
        return cls.objects.order_by("-updated_at").first() or cls()

    def normalized(self):
        """(time, breach, volume) weights scaled to sum to 1, guarding against admin-entered values that don't."""
        total = self.time_weight + self.breach_weight + self.volume_weight
        if total <= 0:
            return (self.time_weight, self.breach_weight, self.volume_weight)
        return (
            self.time_weight / total,
            self.breach_weight / total,
            self.volume_weight / total,
        )


class TaskInstance(models.Model):
    task_id = models.AutoField(primary_key=True)

    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.DO_NOTHING,
        db_column="workflow_instance_id",
        related_name="tasks"
    )

    task_name = models.CharField(max_length=255, null=True)

    created_at = models.DateTimeField()
    status = models.CharField(max_length=50)
    due_at = models.DateTimeField(null=True,blank=True)

    assigned_role_id = models.IntegerField(null=True)

    sla_hours = models.FloatField()
    completed_at = models.DateTimeField(null=True)

    sla_status = models.CharField(max_length=50, null=True)
    # Kept separately from ``completed_at`` so an SLA decision has an
    # auditable evaluation timestamp.
    sla_evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "analytics_task_instance"
