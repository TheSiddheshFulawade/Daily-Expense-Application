from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('email-balance-sheet/', BalanceSheetEmailView.as_view(), name='email_balance_sheet'),
    path('balance-sheet/', BalanceSheetView.as_view(), name='balance_sheet'),
]
