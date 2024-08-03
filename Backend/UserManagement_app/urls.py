from django.urls import path, include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserCreateView.as_view(), name='user-list-create'),
    path('list-details/', UserDetailView.as_view(), name='user-detail'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('register/update/', UserUpdateView.as_view(), name='user-update'),
]
