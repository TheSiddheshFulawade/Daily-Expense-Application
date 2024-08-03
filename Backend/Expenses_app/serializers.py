from rest_framework import serializers, status
from .models import *
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Sum

# Group expense serializer 
class GroupExpenseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupExpenseDetail
        fields = ['id', 'name', 'username', 'email', 'amount', 'note', 'is_paid']
        extra_kwargs = {
            'amount': {'required': False},
            'username': {'required': False},
            'email': {'required': False},
            'is_paid': {'required': False}
        }

     # Checking whether the username or email is provided
    def validate(self, data):
        if not data.get('username') and not data.get('email'):
            raise serializers.ValidationError("Either username or email must be provided.")
        return data

# Serializer for expenses
class ExpenseSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    group_details = GroupExpenseDetailSerializer(many=True, required=False)

    class Meta:
        model = Expense
        fields = ['id', 'date', 'name', 'amount', 'note', 'expense_type', 'split_type', 'total_friends', 'include_self', 'group_details']

    def to_internal_value(self, data):
        # include_self default value is true
        if 'include_self' not in data:
            data['include_self'] = True
        return super().to_internal_value(data)

    def validate(self, data):
        expense_type = data.get('expense_type')
        split_type = data.get('split_type')
        group_details = data.get('group_details', [])
        total_amount = data.get('amount')
        total_friends = data.get('total_friends')
        include_self = data.get('include_self')

        if self.instance:
            expense_type = expense_type or self.instance.expense_type
            split_type = split_type or self.instance.split_type
            total_friends = total_friends or self.instance.total_friends
            include_self = include_self if include_self is not None else self.instance.include_self

        # Checking group expense details
        if expense_type == 'Group':
            if not group_details:
                raise serializers.ValidationError("Group details are required for group expenses.")

            # Counting of entries in group_details
            expected_group_details_count = total_friends if include_self else total_friends

            if 'include_self' not in data:
                data['include_self'] = True

            if len(group_details) != expected_group_details_count:
                raise serializers.ValidationError(
                    f"Number of friends provided ({len(group_details)}) does not match the expected count ({expected_group_details_count})."
                )
            
            if split_type == 'Equal':
                equal_share = total_amount / total_friends
                for detail in group_details:
                    detail['amount'] = equal_share
            elif split_type == 'Exact':
                for detail in group_details:
                    if 'amount' not in detail or detail['amount'] is None:
                        raise serializers.ValidationError("Amount is required for 'Exact' split type.")
            elif split_type == 'Percentage':
                total_percentage = sum(detail.get('amount', 0) for detail in group_details)
                if include_self:
                    if total_percentage >= 100:
                        raise serializers.ValidationError("Total percentage exceeds 100% when including self.")
                else:
                    if abs(total_percentage - 100) > 0.01:  
                        raise serializers.ValidationError("Total percentage must equal 100% when not including self.")

            self.validate_group_details(group_details)
        else:
            if group_details:
                raise serializers.ValidationError("Group details should not be provided for personal expenses.")

        return data

    # Checking the individual group details
    def validate_group_details(self, group_details):
        errors = []
        seen_usernames = set()
        seen_emails = set()
        unregistered_usernames = []

        for detail in group_details:
            username = detail.get('username')
            email = detail.get('email')
            
            if username:
                if username in seen_usernames:
                    errors.append(f"Duplicate entry found for username '{username}'.")
                else:
                    seen_usernames.add(username)
                    if not CustomUser.objects.filter(username=username).exists():
                        unregistered_usernames.append(username)
                        detail['username'] = None  
                        errors.append(f"Username '{username}' is not registered. Please enter an email address instead.")
            elif email:
                if email in seen_emails:
                    errors.append(f"Duplicate entry found for email '{email}'.")
                else:
                    seen_emails.add(email)
            else:
                errors.append("Either username or email must be provided for each group member.")

        if errors:
            raise serializers.ValidationError({"group_details": errors})

        return group_details

    def create(self, validated_data):
        group_details_data = validated_data.pop('group_details', [])
        expense = Expense.objects.create(**validated_data)
        return expense

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.expense_type == 'Group':
            representation['group_details'] = GroupExpenseDetailSerializer(
                instance.group_details.all(), many=True
            ).data
        return representation
    
    def update(self, instance, validated_data):
        group_details_data = validated_data.pop('group_details', None)
        
        # Update the expense instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle group details if provided and if it's a group expense
        if group_details_data is not None and instance.expense_type == 'Group':
            # Delete existing group details
            instance.group_details.all().delete()
            
            total_amount = Decimal(instance.amount)
            total_participants = instance.total_friends + (1 if instance.include_self else 0)

            if instance.split_type == 'Equal':
                equal_share = total_amount / total_participants
                for detail_data in group_details_data:
                    GroupExpenseDetail.objects.create(
                        expense=instance,
                        name=detail_data['name'],
                        username=detail_data.get('username'),
                        email=detail_data.get('email'),
                        amount=equal_share,
                        note=detail_data.get('note', ''),
                        is_paid=detail_data.get('is_paid', False)
                    )
                if instance.include_self:
                    GroupExpenseDetail.objects.create(
                        expense=instance,
                        name=instance.user.get_full_name() or instance.user.username,
                        username=instance.user.username,
                        email=instance.user.email,
                        amount=equal_share,
                        note='Owner\'s share',
                        is_paid=True
                    )

            elif instance.split_type == 'Exact':
                total_friends_amount = sum(Decimal(detail['amount']) for detail in group_details_data)
                for detail_data in group_details_data:
                    GroupExpenseDetail.objects.create(
                        expense=instance,
                        name=detail_data['name'],
                        username=detail_data.get('username'),
                        email=detail_data.get('email'),
                        amount=detail_data['amount'],
                        note=detail_data.get('note', ''),
                        is_paid=detail_data.get('is_paid', False)
                    )
                if instance.include_self:
                    owner_amount = total_amount - total_friends_amount
                    GroupExpenseDetail.objects.create(
                        expense=instance,
                        name=instance.user.get_full_name() or instance.user.username,
                        username=instance.user.username,
                        email=instance.user.email,
                        amount=owner_amount,
                        note='Owner\'s share',
                        is_paid=True
                    )
                else:
                    if total_friends_amount != total_amount:
                        raise serializers.ValidationError("Total of friends' amounts must equal the total expense amount when not including self.")

            elif instance.split_type == 'Percentage':
                total_percentage = sum(Decimal(detail['amount']) for detail in group_details_data)
                for detail_data in group_details_data:
                    percentage = Decimal(detail_data['amount'])
                    amount = (percentage / 100) * total_amount
                    GroupExpenseDetail.objects.create(
                        expense=instance,
                        name=detail_data['name'],
                        username=detail_data.get('username'),
                        email=detail_data.get('email'),
                        amount=amount,
                        note=detail_data.get('note', ''),
                        is_paid=detail_data.get('is_paid', False)
                    )
                if instance.include_self:
                    owner_percentage = 100 - total_percentage
                    owner_amount = (owner_percentage / 100) * total_amount
                    GroupExpenseDetail.objects.create(
                        expense=instance,
                        name=instance.user.get_full_name() or instance.user.username,
                        username=instance.user.username,
                        email=instance.user.email,
                        amount=owner_amount,
                        note='Owner\'s share',
                        is_paid=True
                    )
                else:
                    if total_percentage != 100:
                        raise serializers.ValidationError("Total percentage must equal 100% when not including self.")

        return instance

# Serializer for updating group expense
class UpdateGroupExpenseDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupExpenseDetail
        fields = ['id', 'name', 'username', 'email', 'amount', 'note', 'is_paid']
        extra_kwargs = {
            'id': {'read_only': True},
            'amount': {'required': False},
            'username': {'required': False},
            'email': {'required': False},
            'is_paid': {'required': False}
        }

    def validate(self, data):
        if not data.get('username') and not data.get('email'):
            raise serializers.ValidationError("Either username or email must be provided.")
        return data

# Getting expense portfolio summary
class ExpensePortfolioSummaryView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Get all expenses for the user
        expenses = Expense.objects.filter(user=user)
        personal_expense_count = expenses.filter(expense_type='Personal').count()
        group_expense_count = expenses.filter(expense_type='Group').count()
        personal_expense_sum = expenses.filter(expense_type='Personal').aggregate(Sum('amount'))['amount__sum'] or 0
        group_expenses = expenses.filter(expense_type='Group')
        group_expense_details = GroupExpenseDetail.objects.filter(expense__in=group_expenses)
        
        # Payments received and pending
        payments_received = group_expense_details.filter(is_paid=True).aggregate(Sum('amount'))['amount__sum'] or 0
        payments_pending = group_expense_details.filter(is_paid=False).aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Counting paid and unpaid expenses
        paid_count = group_expense_details.filter(is_paid=True).count()
        unpaid_count = group_expense_details.filter(is_paid=False).count()
        
        # Total spend on group expense (excluding owner's share)
        group_expense_spend = group_expenses.aggregate(Sum('amount'))['amount__sum'] or 0
        owner_share = group_expense_details.filter(username=user.username).aggregate(Sum('amount'))['amount__sum'] or 0
        total_group_spend = group_expense_spend - owner_share
        
        # Summary data
        summary = {
            'personal_expense_count': personal_expense_count,
            'group_expense_count': group_expense_count,
            'personal_expense_sum': personal_expense_sum,
            'group_expense_summary': {
                'payments_received': payments_received,
                'payments_pending': payments_pending,
                'paid_count': paid_count,
                'unpaid_count': unpaid_count,
                'total_spend(Group Expense - My Expense)': total_group_spend,
            },
            'total_expense_sum': personal_expense_sum + group_expense_spend,
        }
        
        return Response(summary, status=status.HTTP_200_OK)

# Serializer for unpaid expense
class UnpaidExpenseSerializer(serializers.ModelSerializer):
    expense_name = serializers.CharField(source='expense.name')
    expense_note = serializers.CharField(source='expense.note')

    class Meta:
        model = GroupExpenseDetail
        fields = ['id', 'name', 'username', 'email', 'amount', 'note', 'expense_name', 'expense_note']