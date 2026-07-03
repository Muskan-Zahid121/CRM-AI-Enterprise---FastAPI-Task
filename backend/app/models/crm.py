from tortoise import fields
from tortoise.models import Model


class Customer(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="customers")
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, null=True)
    phone = fields.CharField(max_length=50, null=True)
    company = fields.CharField(max_length=255, null=True)
    industry = fields.CharField(max_length=100, null=True)
    status = fields.CharField(max_length=20, default="active")
    notes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "customers"


class Contact(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="contacts")
    customer = fields.ForeignKeyField("models.Customer", related_name="contacts", null=True)
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, null=True)
    phone = fields.CharField(max_length=50, null=True)
    title = fields.CharField(max_length=100, null=True)
    is_primary = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "contacts"


class Lead(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="leads")
    name = fields.CharField(max_length=255)
    email = fields.CharField(max_length=255, null=True)
    company = fields.CharField(max_length=255, null=True)
    source = fields.CharField(max_length=100, null=True)
    stage = fields.CharField(max_length=30, default="new")
    score = fields.IntField(default=0)
    notes = fields.TextField(null=True)
    converted_customer_id = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "leads"


class Deal(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="deals")
    customer = fields.ForeignKeyField("models.Customer", related_name="deals", null=True)
    lead = fields.ForeignKeyField("models.Lead", related_name="deals", null=True)
    title = fields.CharField(max_length=255)
    value = fields.DecimalField(max_digits=12, decimal_places=2, default=0)
    stage = fields.CharField(max_length=30, default="lead")
    probability = fields.IntField(default=0)
    expected_close_date = fields.DateField(null=True)
    notes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "deals"


class Note(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="notes")
    customer = fields.ForeignKeyField("models.Customer", related_name="crm_notes", null=True)
    deal = fields.ForeignKeyField("models.Deal", related_name="deal_notes", null=True)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "notes"


class Document(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="documents")
    title = fields.CharField(max_length=255)
    content = fields.TextField()
    file_path = fields.CharField(max_length=500, null=True)
    file_type = fields.CharField(max_length=50, default="text")
    tags = fields.JSONField(default=list)
    indexed = fields.BooleanField(default=False)
    chunk_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "documents"


class Meeting(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="meetings")
    customer = fields.ForeignKeyField("models.Customer", related_name="meetings", null=True)
    title = fields.CharField(max_length=255)
    transcript = fields.TextField(null=True)
    summary = fields.TextField(null=True)
    action_items = fields.JSONField(default=list)
    participants = fields.JSONField(default=list)
    recording_path = fields.CharField(max_length=500, null=True)
    meeting_date = fields.DatetimeField(null=True)
    duration_minutes = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "meetings"


class Task(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="tasks")
    assignee = fields.ForeignKeyField("models.User", related_name="assigned_tasks", null=True)
    customer = fields.ForeignKeyField("models.Customer", related_name="tasks", null=True)
    deal = fields.ForeignKeyField("models.Deal", related_name="tasks", null=True)
    meeting = fields.ForeignKeyField("models.Meeting", related_name="tasks", null=True)
    title = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    priority = fields.CharField(max_length=20, default="medium")
    status = fields.CharField(max_length=20, default="pending")
    due_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "tasks"


class Activity(Model):
    id = fields.IntField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="activities")
    customer = fields.ForeignKeyField("models.Customer", related_name="activities", null=True)
    activity_type = fields.CharField(max_length=50)
    description = fields.TextField()
    metadata = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "activities"
