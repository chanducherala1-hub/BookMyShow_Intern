from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import Avg
from django.conf import settings
from users.models import User
import random 
from django.utils import timezone


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Language(models.Model):
    language = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.language


class CastMember(models.Model):
    ROLE_CHOICES = [
        ("Actor", "Actor"),
        ("Actress", "Actress"),
        ("Director", "Director"),
        ("Producer", "Producer"),
        ("Music Director", "Music Director"),
        ("Writer", "Writer"),
    ]

    name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    image = models.ImageField(upload_to="cast/", blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Movie(models.Model):
    CERTIFICATION_CHOICES = [
        ("U", "Universal"),
        ("UA", "U/A"),
        ("A", "Adults Only"),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    release_date = models.DateField()
    duration_minutes = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    age_certification = models.CharField(max_length=5, choices=CERTIFICATION_CHOICES)
    youtube_trailer_url = models.URLField(
    max_length=255,
    blank=True,
    null=True
    )

    genres = models.ManyToManyField(Genre, related_name="movies")
    languages = models.ManyToManyField(Language, related_name="movies")
    cast = models.ManyToManyField(CastMember, related_name="movies", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    @property
    def average_rating(self):
        if not hasattr(self, 'reviews'):
            return 0.0
        avg = self.reviews.filter(is_approved=True).aggregate(Avg("rating"))["rating__avg"]
        return round(avg, 1) if avg else 0.0

    def __str__(self):
        return self.title


class MovieImage(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="movies/posters/")
    is_primary = models.BooleanField(default=False, help_text="Main poster image")

    def __str__(self):
        return f"{self.movie.title} Image"
    

class Theater(models.Model):
    theater_name = models.CharField(max_length=100, unique=True)
    city = models.CharField(max_length=100) 
    address = models.CharField(max_length=250)
    phone_number = models.CharField(max_length=12)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.theater_name} ({self.city})'


class Screen(models.Model):
    SCREEN_TYPE_CHOICES = [
        ("2D", "2D"),
        ("3D", "3D"),
        ("IMAX", "IMAX"),
        ("4DX", "4DX"),
        ("ScreenX", "ScreenX"),
    ]
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name="screens")
    screen_number = models.PositiveSmallIntegerField()
    total_seats = models.PositiveIntegerField()
    screen_type = models.CharField(max_length=20, choices=SCREEN_TYPE_CHOICES)

    def __str__(self):
        return f"{self.theater.theater_name} - Screen {self.screen_number} ({self.screen_type})"


class Show(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="shows")
    screen = models.ForeignKey(
    Screen,
    on_delete=models.CASCADE,
    related_name="shows",
    null=True,
    blank=True,
    )
    show_time = models.TimeField()
    show_date = models.DateField()


    ticket_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return f"{self.movie.title} - {self.show_date} @ {self.show_time}"

    
class Seat(models.Model):
    screen = models.ForeignKey(
        Screen,
        on_delete=models.CASCADE,
        related_name="seats"
    )

    seat_number = models.CharField(max_length=5)

    is_booked = models.BooleanField(default=False)

    def __str__(self):
        return self.seat_number

class SeatLock(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    show = models.ForeignKey(Show, on_delete=models.CASCADE)
    seat = models.ForeignKey(
    "Seat",
    on_delete=models.CASCADE,
    related_name="seat_locks"
)
    locked_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

from django.db import models
from django.conf import settings
import uuid

class Booking(models.Model):

    PAYMENT_STATUS = [
        ("Pending", "Pending"),
        ("Success", "Success"),
        ("Failed", "Failed"),
    ]

    BOOKING_STATUS = [
        ("Confirmed", "Confirmed"),
        ("Cancelled", "Cancelled"),
    ]

    booking_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    show = models.ForeignKey(
        Show,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    seats = models.ManyToManyField(
        Seat,
        related_name="bookings"
    )

    booking_time = models.DateTimeField(auto_now_add=True)

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="Pending"
    )

    booking_status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS,
        default="Confirmed"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking_id} - {self.user.username}"


class Review(models.Model):
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    booking = models.ForeignKey(
    Booking,
    on_delete=models.CASCADE,
    related_name="reviews",
    null=True,
    blank=True
    )
    rating = models.PositiveSmallIntegerField()

    review = models.TextField()

    verified_viewer = models.BooleanField(default=False)

    is_approved = models.BooleanField(default=True)

    is_reported = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.movie.title} - {self.user.username}"



class Order(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    booking = models.ForeignKey(
        "Booking",
        on_delete=models.CASCADE
    )

    razorpay_order_id = models.CharField(
        max_length=100,
        unique=True
    )

    razorpay_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Success", "Success"),
            ("Failed", "Failed"),
        ],
        default="Pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
