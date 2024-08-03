from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserListCreateView.as_view(), name='user-list-create'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/update/', UserUpdateView.as_view(), name='user-update'),
]
