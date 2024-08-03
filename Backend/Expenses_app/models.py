from django.db import models
from UserManagement_app.models import *

class Expense(models.Model):
    EXPENSE_TYPE_CHOICES = [
        ('Personal', 'Personal'),
        ('Group', 'Group'),
    ]

    SPLIT_TYPE_CHOICES = [
        ('Equal', 'Equal'),
        ('Exact', 'Exact'),
        ('Percentage', 'Percentage'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='expenses')
    date = models.DateField()
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(null=True, blank=True)
    expense_type = models.CharField(max_length=10, choices=EXPENSE_TYPE_CHOICES)
    split_type = models.CharField(max_length=10, choices=SPLIT_TYPE_CHOICES, null=True, blank=True)
    total_friends = models.IntegerField(null=True, blank=True)
    include_self = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class GroupExpenseDetail(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='group_details')
    name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return self.name
