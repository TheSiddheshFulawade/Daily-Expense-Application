from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import *
from .tasks import *
from Expenses_app.models import *
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from daily_expense_system.settings import EMAIL_HOST_USER
from django.utils import timezone
from datetime import datetime, timedelta 

CustomUser = get_user_model()

class SendExpenseNotificationView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ExpenseNotificationSerializer(data=request.data)
        if serializer.is_valid():
            expense_id = serializer.validated_data['expense_id']
            try:
                expense = Expense.objects.get(id=expense_id, user=request.user)
            except Expense.DoesNotExist:
                return Response({"error": "Expense not found or you don't have permission."}, status=status.HTTP_404_NOT_FOUND)

            try:
                # Use the create method from the serializer
                notification = serializer.save()

                if notification.notification_status:
                    self.send_immediate_notifications(notification)
                    notification.schedule_reminders()
                
                return Response({"message": "Notification updated and reminders scheduled successfully."}, status=status.HTTP_200_OK)
            except IntegrityError:
                return Response({"error": "An error occurred while saving the notification."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def send_immediate_notifications(self, notification):
        expense = notification.expense
        unpaid_details = GroupExpenseDetail.objects.filter(expense=expense, is_paid=False).exclude(username=expense.user.username)

        for detail in unpaid_details:
            recipient_email = detail.email if detail.email else CustomUser.objects.get(username=detail.username).email
            self.send_notification_email(detail, expense, notification.due_date, notification.due_time, recipient_email)

    def send_notification_email(self, detail, expense, due_date, due_time, recipient_email):
        subject = f"Payment Reminder for {expense.name}"
        message = f"""
        Dear {detail.name},
        This is a reminder for your pending payment for the group expense "{expense.name}".
        Details:
        - Amount due: ₹{detail.amount}
        - Due date: {due_date}
        - Due time: {due_time}
        - Expense note: {expense.note}
        - Your personal note: {detail.note}
        Please ensure that the payment is made by the due date and time.
        Thank you for your cooperation.
        Best regards,
        {expense.user.get_full_name() or expense.user.username}
        """
        send_mail(
            subject,
            message,
            EMAIL_HOST_USER,
            [recipient_email],
            fail_silently=False,
        )

    def schedule_reminders(self, notification):
        due_datetime = timezone.make_aware(datetime.combine(notification.due_date, notification.due_time))
        
        # Schedule 24-hour reminder
        schedule_24h, _ = CrontabSchedule.objects.get_or_create(
            minute=due_datetime.minute,
            hour=due_datetime.hour,
            day_of_month=due_datetime.day,
            month_of_year=due_datetime.month,
        )
        PeriodicTask.objects.create(
            crontab=schedule_24h,
            name=f'24h_reminder_for_expense_{notification.expense.id}',
            task='Notification_app.tasks.send_reminder_email',
            args=json.dumps([notification.expense.id, '24 hour']),
            one_off=True,
        )

        # Schedule 1-hour reminder
        one_hour_before = due_datetime - timedelta(hours=1)
        schedule_1h, _ = CrontabSchedule.objects.get_or_create(
            minute=one_hour_before.minute,
            hour=one_hour_before.hour,
            day_of_month=one_hour_before.day,
            month_of_year=one_hour_before.month,
        )
        PeriodicTask.objects.create(
            crontab=schedule_1h,
            name=f'1h_reminder_for_expense_{notification.expense.id}',
            task='Notification_app.tasks.send_reminder_email',
            args=json.dumps([notification.expense.id, '1 hour']),
            one_off=True,
        )

class ExpenseNotificationListAPIView(generics.ListAPIView):
    serializer_class = ExpenseNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filter notifications for the current user
        return ExpenseNotification.objects.filter(expense__user=self.request.user).order_by('-due_date', '-due_time')