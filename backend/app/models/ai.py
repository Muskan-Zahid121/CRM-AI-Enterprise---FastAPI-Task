from tortoise import fields
from tortoise.models import Model


class ChatSession(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="chat_sessions")
    title = fields.CharField(max_length=255, default="New conversation")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chat_sessions"


class ChatMessage(Model):
    id = fields.IntField(pk=True)
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages", null=True)
    owner = fields.ForeignKeyField("models.User", related_name="chat_messages")
    role = fields.CharField(max_length=20, default="user")
    message = fields.TextField()
    response = fields.TextField(null=True)
    agent = fields.CharField(max_length=50, null=True)
    citations = fields.JSONField(default=list)
    context = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"


class Workflow(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="workflows")
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    steps = fields.JSONField(default=list)
    status = fields.CharField(max_length=20, default="draft")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "workflows"


class WorkflowExecution(Model):
    id = fields.IntField(pk=True)
    workflow = fields.ForeignKeyField("models.Workflow", related_name="executions")
    owner = fields.ForeignKeyField("models.User", related_name="workflow_executions")
    status = fields.CharField(max_length=20, default="running")
    result = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "workflow_executions"


class EmailHistory(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="email_history")
    customer = fields.ForeignKeyField("models.Customer", related_name="emails", null=True)
    subject = fields.CharField(max_length=500)
    body = fields.TextField()
    email_type = fields.CharField(max_length=50, default="generated")
    sent = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "email_history"


class Notification(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="notifications")
    title = fields.CharField(max_length=255)
    body = fields.TextField()
    read = fields.BooleanField(default=False)
    notification_type = fields.CharField(max_length=50, default="info")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notifications"


class AuditLog(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="audit_logs")
    action = fields.CharField(max_length=100)
    resource = fields.CharField(max_length=100)
    resource_id = fields.IntField(null=True)
    details = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "audit_logs"
