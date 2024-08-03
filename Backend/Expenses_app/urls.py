from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('expenses/', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('expenses/<int:expense_id>/update-payment/<int:detail_id>/', UpdatePaymentStatusView.as_view(), name='update-payment-status'),
    path('update-expense/', ExpenseUpdateView.as_view(), name='update-expense'),
    path('expenses/<int:expense_id>/group-details/<int:detail_id>/', UpdateGroupExpenseDetailView.as_view(), name='update-group-expense-detail'),
    path('expense-portfolio-summary/', ExpensePortfolioSummaryView.as_view(), name='expense-portfolio-summary'),
    path('delete-expense/<int:expense_id>/', DeleteExpenseView.as_view(), name='delete-expense'),
    path('delete-group-expense-detail/<int:expense_id>/<int:detail_id>/', DeleteGroupExpenseDetailView.as_view(), name='delete-group-expense-detail'),
    path('unpaid-expenses/', UnpaidExpenseListView.as_view(), name='unpaid_expenses'),
    
]

