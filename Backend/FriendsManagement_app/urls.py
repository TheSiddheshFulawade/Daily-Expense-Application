from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('send-friend-request/', SendFriendRequestAPIView.as_view(), name='send_friend_request'),
    path('respond-to-friend-request/', RespondToFriendRequestAPIView.as_view(), name='respond_to_friend_request'),
    path('list-user-friends/', ListUserFriendsAPIView.as_view(), name='list_user_friends'),
    path('list-pending-friend-requests/', ListPendingFriendRequestsAPIView.as_view(), name='list_pending_friend_requests'),
    path('remove-friend/', RemoveFriendAPIView.as_view(), name='remove_friend'),
]
