from django.db import models
from django.contrib.auth.models import AbstractUser
import os

def user_profile_photo_path(instance, filename):
    # path is : media/profile_photos/username/User Icon.jpg
    return os.path.join('profile_photos', instance.username, filename)

class CustomUser(AbstractUser):
    # Adding the additional fields
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=10)
    profile_photo = models.ImageField(upload_to=user_profile_photo_path, default='User Icon.jpg')

    def __str__(self):
        return self.username
