from celery import shared_task
from celery import current_app as app
from django.core.mail import send_mail
from django.conf import settings
from Expenses_app.models import *
from UserManagement_app.models import *
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *
from django.core.mail import send_mail
from daily_expense_system.settings import EMAIL_HOST_USER
from django.utils.timezone import localtime
import logging

CustomUser = get_user_model()
app.conf.enable_utc = False
app.conf.timezone = 'Asia/Kolkata'


# Configure logging
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_reminder_email(self, expense_id, reminder_type):
    logger.info(f"Sending {reminder_type} reminder for expense {expense_id}")
    try:
        expense = Expense.objects.get(id=expense_id)
        notification = expense.notifications.latest('created_at')
        now = timezone.now()
        due_datetime = timezone.make_aware(datetime.combine(notification.due_date, notification.due_time))
        
        if now >= due_datetime:
            logger.info(f"Skipping reminder for expense {expense_id} as it's already due")
            return

        unpaid_details = GroupExpenseDetail.objects.filter(expense=expense, is_paid=False).exclude(username=expense.user.username)
        
        for detail in unpaid_details:
            if detail.is_paid:
                continue
            
            recipient_email = detail.email or CustomUser.objects.get(username=detail.username).email
            subject = f"{reminder_type.capitalize()} Reminder: Payment for {expense.name}"
            message = f"""
            Dear {detail.name},
            This is a reminder that your payment for the group expense "{expense.name}" is due in {reminder_type}.
            Details:
            - Amount due: ₹{detail.amount}
            - Due date and time: {notification.due_date} {notification.due_time}
            - Expense note: {expense.note}
            - Your personal note: {detail.note}
            Please ensure that the payment is made by the due date and time.
            Thank you for your cooperation.
            Best regards,
            {expense.user.get_full_name() or expense.user.username}
            """
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,
                    [recipient_email],
                    fail_silently=False,
                )
                logger.info(f"Reminder email sent to {recipient_email} for expense {expense_id}")
            except Exception as e:
                logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
                raise
        
        return f"Reminder emails sent for expense {expense_id}"
    except Exception as e:
        logger.error(f"Error in send_reminder_email task: {str(e)}")
        raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)

@shared_task(bind=True)
def check_scheduled_reminders(self):
    logger.info("Checking scheduled reminders")
    try:
        now = timezone.localtime(timezone.now())
        notifications = ExpenseNotification.objects.filter(
            notification_status=True,
            due_date__gte=now.date(),
        )

        reminders_sent = 0
        for notification in notifications:
            due_datetime = timezone.localtime(timezone.make_aware(datetime.combine(notification.due_date, notification.due_time)))
            time_until_due = due_datetime - now

            if timedelta(hours=23) <= time_until_due <= timedelta(hours=25):
                send_reminder_email.delay(notification.expense.id, '24 hour')
                reminders_sent += 1
            elif timedelta(minutes=55) <= time_until_due <= timedelta(hours=1, minutes=5):
                send_reminder_email.delay(notification.expense.id, '1 hour')
                reminders_sent += 1

        return f"Checked {notifications.count()} notifications, sent {reminders_sent} reminders"
    except Exception as e:
        self.retry(exc=e, countdown=60)  # Retry after 60 seconds if there's an exception