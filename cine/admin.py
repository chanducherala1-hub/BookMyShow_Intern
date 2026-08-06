from django.contrib import admin
from django.db.models import Sum
from .models import Genre, Language, CastMember, Movie, MovieImage, Screen, Seat, Show, Theater, Order, Booking

admin.site.register([
    Genre,
    Language,
    CastMember,
    Movie,
    MovieImage,
    Theater,
    Show,
    Screen,
    Seat,
])

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_email",
        "amount",
        "payment_status",
    )
    list_filter = ('payment_status',)

    def user_email(self, obj):
        return obj.user.email

    def changelist_view(self, request, extra_context=None):
        total_revenue = Order.objects.filter(payment_status="Success").aggregate(
            total=Sum("amount")
        )["total"] or 0

        extra_context = extra_context or {}
        extra_context['title'] = f"Orders (Total Revenue: ₹{total_revenue:,.2f})"
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_id",
        "user_email",
        "show",
        "get_selected_seats",
        "payment_status",
    )

    def user_email(self, obj):
        return obj.user.email

    def get_selected_seats(self, obj):
        return ", ".join(
            seat.seat_number for seat in obj.seats.all()
        )

    get_selected_seats.short_description = "Selected Seats"