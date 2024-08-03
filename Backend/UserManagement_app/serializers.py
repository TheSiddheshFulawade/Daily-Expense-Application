from rest_framework import serializers
from .models import *

 # Custom serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'profile_photo']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            phone_number=validated_data['phone_number'],
            profile_photo=validated_data.get('profile_photo', 'User Icon.jpg')
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
