from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Screen, Seat


@receiver(post_save, sender=Screen)
def create_screen_seats(sender, instance, created, **kwargs):

    if not created:
        return

    seats = []

    for number in range(1, instance.total_seats + 1):

        seats.append(
            Seat(
                screen=instance,
                seat_number=f"S{number}"
            )
        )

    Seat.objects.bulk_create(seats)