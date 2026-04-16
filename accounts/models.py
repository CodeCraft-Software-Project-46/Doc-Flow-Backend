from django.contrib.auth.models import User
from django.db import models

# We create a Profile linked One-to-One with Django's default User
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f"{self.user.username}'s Profile"
