from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *

class SendFriendRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        receiver_username = request.data.get('receiver_username')
        sender = request.user

        if sender.username == receiver_username:
            return Response({'error': "Cannot send friend request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        receiver = CustomUser.objects.filter(username=receiver_username).first()
        if not receiver:
            return Response({'error': "Receiver user not found."}, status=status.HTTP_400_BAD_REQUEST)

        friend_list, _ = FriendList.objects.get_or_create(user=sender)
        if friend_list.is_mutual_friend(receiver):
            return Response({'error': "You are already friends with this user."}, status=status.HTTP_400_BAD_REQUEST)

        existing_request = FriendRequest.objects.filter(sender=sender, receiver=receiver, status='Pending').first()
        if existing_request:
            return Response({'message': "Friend request already sent. Please wait for acceptance."}, status=status.HTTP_400_BAD_REQUEST)

        friend_request = FriendRequest.objects.create(sender=sender, receiver=receiver)
        serializer = FriendRequestSerializer(friend_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class RespondToFriendRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sender_username = request.data.get('sender_username')
        action = request.data.get('action')

        if not sender_username or action not in ['accept', 'decline']:
            return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)

        sender = CustomUser.objects.filter(username=sender_username).first()
        if not sender:
            return Response({'error': "Sender user not found."}, status=status.HTTP_400_BAD_REQUEST)

        friend_request = FriendRequest.objects.filter(sender=sender, receiver=request.user, status='Pending').first()
        if not friend_request:
            return Response({'error': "Friend request not found."}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'accept':
            friend_request.accept()
            message = 'Friend request accepted successfully'
        else:
            friend_request.decline()
            message = 'Friend request declined successfully'

        return Response({'message': message}, status=status.HTTP_200_OK)

class ListUserFriendsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friend_list, _ = FriendList.objects.get_or_create(user=request.user)
        serializer = FriendListSerializer(friend_list)
        return Response(serializer.data)

class ListPendingFriendRequestsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pending_requests = FriendRequest.objects.filter(receiver=request.user, status='Pending')
        serializer = FriendRequestSerializer(pending_requests, many=True)
        return Response(serializer.data)

class RemoveFriendAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        username_to_remove = request.data.get('username')
        user = request.user

        if not username_to_remove:
            return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)

        user_to_remove = CustomUser.objects.filter(username=username_to_remove).first()
        if not user_to_remove:
            return Response({'error': "User not found."}, status=status.HTTP_400_BAD_REQUEST)

        friend_list, _ = FriendList.objects.get_or_create(user=user)
        if not friend_list.is_mutual_friend(user_to_remove):
            return Response({'error': "You are not friends with this user."}, status=status.HTTP_400_BAD_REQUEST)

        friend_list.unfriend(user_to_remove)

        return Response({'message': 'Friend removed successfully'}, status=status.HTTP_200_OK)
