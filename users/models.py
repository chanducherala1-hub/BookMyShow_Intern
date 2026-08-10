from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    full_name = models.CharField(max_length=100)

    phone_number = models.CharField(
        max_length=15,
        unique=True
    )

    profile_image = models.ImageField(
        upload_to="users/profile/",
        blank=True,
        null=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    is_verified = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.full_name