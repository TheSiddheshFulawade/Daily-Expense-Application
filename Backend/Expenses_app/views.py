from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import *
from .serializers import *
from UserManagement_app.models import *
from UserManagement_app.serializers import *
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
import csv
import io

 # Listing and creating expenses
class ExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        expense = self.perform_create(serializer)
        
        if expense.expense_type == 'Group':
            group_details_data = serializer.validated_data.get('group_details', [])
            self.handle_group_expense(expense, group_details_data)
        
        # Re-fetching the expense to get the updated data including the new group details
        updated_serializer = self.get_serializer(expense)
        headers = self.get_success_headers(updated_serializer.data)
        return Response(updated_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        return serializer.save(user=self.request.user)

    def handle_group_expense(self, expense, group_details_data):
        split_type = expense.split_type
        total_amount = expense.amount
        total_friends = expense.total_friends

        # Actual number of participants
        actual_participants = total_friends + 1 if expense.include_self else total_friends

        if split_type == 'Equal':
            equal_share = total_amount / actual_participants
            
            for detail_data in group_details_data:
                GroupExpenseDetail.objects.create(
                    expense=expense,
                    name=detail_data['name'],
                    username=detail_data.get('username'),
                    email=detail_data.get('email'),
                    amount=equal_share,
                    note=detail_data.get('note', ''),
                    is_paid=False
                )

            # Create group expense detail for the current user if include_self is True
            if expense.include_self:
                GroupExpenseDetail.objects.create(
                    expense=expense,
                    name=expense.user.get_full_name() or expense.user.username,
                    username=expense.user.username,
                    email=expense.user.email,
                    amount=equal_share,
                    note='Owner\'s share',
                    is_paid=True
                )

        elif split_type == 'Exact':
            # Calculate the sum
            friends_total = sum(detail['amount'] for detail in group_details_data)

            # Check if the sum matches the total amount
            if not expense.include_self:
                if abs(friends_total - total_amount) > 0.01:  
                    raise serializers.ValidationError(
                        f"The sum of amounts ({friends_total}) does not match the total expense amount ({total_amount})"
                    )
            
            for detail_data in group_details_data:
                GroupExpenseDetail.objects.create(
                    expense=expense,
                    name=detail_data['name'],
                    username=detail_data.get('username'),
                    email=detail_data.get('email'),
                    amount=detail_data['amount'],
                    note=detail_data.get('note', ''),
                    is_paid=False
                )

            # Create a group expense for the current user if include_self value is True
            if expense.include_self:
                user_amount = total_amount - friends_total
                GroupExpenseDetail.objects.create(
                    expense=expense,
                    name=expense.user.get_full_name() or expense.user.username,
                    username=expense.user.username,
                    email=expense.user.email,
                    amount=user_amount,
                    note='Owner\'s share',
                    is_paid=True
                )

        elif split_type == 'Percentage':
            total_percentage = sum(detail['amount'] for detail in group_details_data)
            for detail_data in group_details_data:
                amount = (detail_data['amount'] / 100) * total_amount
                GroupExpenseDetail.objects.create(
                    expense=expense,
                    name=detail_data['name'],
                    username=detail_data.get('username'),
                    email=detail_data.get('email'),
                    amount=amount,
                    note=detail_data.get('note', ''),
                    is_paid=False
                )

            if expense.include_self:
                user_percentage = 100 - total_percentage
                user_amount = (user_percentage / 100) * total_amount
                GroupExpenseDetail.objects.create(
                    expense=expense,
                    name=expense.user.get_full_name() or expense.user.username,
                    username=expense.user.username,
                    email=expense.user.email,
                    amount=user_amount,
                    note='Owner\'s share',
                    is_paid=True
                )
            else:
                # Check that the percentages adds up to 100%
                if abs(total_percentage - 100) > 0.01:  
                    raise serializers.ValidationError("Total percentage must equal 100% when not including self.")

class UpdatePaymentStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, expense_id, detail_id):
        try:
            expense = Expense.objects.get(id=expense_id, user=request.user)
            detail = GroupExpenseDetail.objects.get(id=detail_id, expense=expense)
        except (Expense.DoesNotExist, GroupExpenseDetail.DoesNotExist):
            return Response({"error": "Expense or detail not found"}, status=status.HTTP_404_NOT_FOUND)

        is_paid = request.data.get('is_paid')
        if is_paid is not None:
            detail.is_paid = is_paid
            detail.save()
            return Response({"message": "Payment status updated successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "is_paid field is required"}, status=status.HTTP_400_BAD_REQUEST)
        
class ExpenseUpdateView(generics.UpdateAPIView):
    serializer_class = ExpenseSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        expense_id = request.data.get('id')
        if not expense_id:
            return Response({"error": "Expense ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = self.get_queryset().get(id=expense_id)
        except Expense.DoesNotExist:
            return Response({"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        # Perform the update (this will now handle the recalculation)
        updated_instance = serializer.save()

        # Re fetch the instance to get updated data
        updated_serializer = self.get_serializer(updated_instance)
        return Response(updated_serializer.data)

    def perform_update(self, serializer):
        serializer.save()

class UpdateGroupExpenseDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, expense_id, detail_id):
        try:
            expense = Expense.objects.get(id=expense_id, user=request.user)
            detail = GroupExpenseDetail.objects.get(id=detail_id, expense=expense)
        except Expense.DoesNotExist:
            return Response({"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND)
        except GroupExpenseDetail.DoesNotExist:
            return Response({"error": "Group expense detail not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateGroupExpenseDetailSerializer(detail, data=request.data, partial=True)
        if serializer.is_valid():
            try:
                self.validate_update(expense, detail, serializer.validated_data)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            updated_detail = serializer.save()
            return Response(UpdateGroupExpenseDetailSerializer(updated_detail).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def validate_update(self, expense, detail, validated_data):
        # Check for duplicate entries
        username = validated_data.get('username')
        email = validated_data.get('email')

        if username:
            if GroupExpenseDetail.objects.filter(expense=expense, username=username).exclude(id=detail.id).exists():
                raise ValidationError(f"Duplicate entry found for username '{username}'.")
            
            # Check if username exists in model
            if not CustomUser.objects.filter(username=username).exists():
                raise ValidationError(f"Username '{username}' is not registered. Please enter an email address instead.")

        if email:
            if GroupExpenseDetail.objects.filter(expense=expense, email=email).exclude(id=detail.id).exists():
                raise ValidationError(f"Duplicate entry found for email '{email}'.")

        # Validate amount if it's being updated
        if 'amount' in validated_data:
            new_amount = validated_data['amount']
            old_amount = detail.amount
            total_difference = new_amount - old_amount

            if expense.split_type == 'Exact':
                new_total = expense.amount + total_difference
                if new_total <= 0:
                    raise ValidationError("The new total amount must be greater than zero.")

            elif expense.split_type == 'Percentage':
                all_details = expense.group_details.all()
                total_percentage = sum(d.amount for d in all_details if d.id != detail.id) + new_amount
                if expense.include_self:
                    if total_percentage >= 100:
                        raise ValidationError("Total percentage exceeds 100% when including self.")
                else:
                    if abs(total_percentage - 100) > 0.01:  
                        raise ValidationError("Total percentage must equal 100% when not including self.")

        # Ensuring either username or email is provided
        if not username and not email:
            raise ValidationError("Either username or email must be provided.")

        return True
    
class DeleteExpenseView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, expense_id):
        try:
            expense = Expense.objects.get(id=expense_id, user=request.user)
            expense.delete()
            return Response({"message": "Expense deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist:
            return Response({"error": "Expense not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DeleteGroupExpenseDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, expense_id, detail_id):
        try:
            expense = Expense.objects.get(id=expense_id, user=request.user)
            detail = GroupExpenseDetail.objects.get(id=detail_id, expense=expense)
            detail.delete()
            return Response({"message": "Group expense detail deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist:
            return Response({"error": "Expense or group expense detail not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UnpaidExpenseListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        unpaid_expenses = GroupExpenseDetail.objects.filter(
            expense__user=user,
            is_paid=False
        ).exclude(username=user.username)  # Exclude the user's own expenses

        serializer = UnpaidExpenseSerializer(unpaid_expenses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
