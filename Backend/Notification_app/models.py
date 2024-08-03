from django.db import models
from django.contrib.auth import get_user_model
from Expenses_app.models import Expense
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import IntegrityError

User = get_user_model()

class ExpenseNotification(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='notifications')
    due_date = models.DateField()
    due_time = models.TimeField()
    notification_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    twenty_four_hour_reminder_sent = models.BooleanField(default=False)
    one_hour_reminder_sent = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and self.notification_status:
            self.schedule_reminders()

    def schedule_reminders(self):
        now = timezone.now()
        due_datetime = timezone.make_aware(datetime.combine(self.due_date, self.due_time))
        time_until_due = due_datetime - now

        if time_until_due > timedelta(hours=24):
            self.schedule_reminder('24 hour', due_datetime - timedelta(hours=24))
            self.schedule_reminder('1 hour', due_datetime - timedelta(hours=1))
        elif timedelta(hours=1) < time_until_due <= timedelta(hours=24):
            self.schedule_reminder('1 hour', due_datetime - timedelta(hours=1))
        # If less than 1 hour left, we will not schedule any reminder

    def schedule_reminder(self, reminder_type, reminder_time):
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=reminder_time.minute,
            hour=reminder_time.hour,
            day_of_month=reminder_time.day,
            month_of_year=reminder_time.month,
        )

        task_name = f'{reminder_type}_reminder_for_expense_{self.expense.id}'
        task_data = {
            'crontab': schedule,
            'name': task_name,
            'task': 'Notification_app.tasks.send_reminder_email',
            'args': json.dumps([self.expense.id, reminder_type]),
            'one_off': True,
        }

        PeriodicTask.objects.update_or_create(
            name=task_name,
            defaults=task_data
        )
