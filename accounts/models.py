from django.contrib.auth.models import AbstractUser, User, AbstractUser
from django.db import models

# We create a Profile linked One-to-One with Django's default User
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    department = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f"{self.user.username}'s Profile"


class UserData(models.Model):
    # Django needs to know the ID exists to do lookups
    id = models.CharField(primary_key=True, max_length=255)
    
    # Map the specific fields you need from the screenshot
    username = models.CharField(max_length=150)
    email = models.EmailField()
    contact_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False  # The "Magic" setting: Django won't touch the DB structure
        db_table = 'user_user' # The exact name of your teammate's table

    def __str__(self):
        return self.username