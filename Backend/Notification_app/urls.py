from django.urls import path, include
from rest_framework.routers import DefaultRouter
from Expenses_app.views import *
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('send-expense-notification/', SendExpenseNotificationView.as_view(), name='send_expense_notification'),
    path('notifications/', ExpenseNotificationListAPIView.as_view(), name='notification-list'),
    
]