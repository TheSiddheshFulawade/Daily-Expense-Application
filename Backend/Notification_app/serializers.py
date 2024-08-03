from rest_framework import serializers
from Expenses_app.models import Expense
from .models import ExpenseNotification

class ExpenseNotificationSerializer(serializers.ModelSerializer):
    expense_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ExpenseNotification
        fields = ['expense_id', 'notification_status', 'due_date', 'due_time']

    def validate_expense_id(self, value):
        try:
            expense = Expense.objects.get(id=value, expense_type='Group')
        except Expense.DoesNotExist:
            raise serializers.ValidationError("Invalid expense ID or not a group expense.")
        return value

    def create(self, validated_data):
        expense_id = validated_data.pop('expense_id')
        expense = Expense.objects.get(id=expense_id)
        
        # Checking if the notification already exists for this expense
        existing_notification = ExpenseNotification.objects.filter(expense=expense).first()
        if existing_notification:
            # Update the existing notification
            for key, value in validated_data.items():
                setattr(existing_notification, key, value)
            existing_notification.save()
            return existing_notification
        else:
            # Create a new notification
            return ExpenseNotification.objects.create(expense=expense, **validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['expense_id'] = instance.expense.id
        return representation