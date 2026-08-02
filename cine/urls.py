from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("details/<int:movie_id>/", views.details, name="details"),
    path("books/<int:movie_id>/", views.books, name="books"),
    path("seats/<int:show_id>/", views.seats, name="seats"),
     path(
    "lock-seats/<int:show_id>/",
    views.lock_seats,
    name="lock_seats"
    ),
    path(
    "movie/<int:movie_id>/reviews/",
    views.show_reviews,
    name="show_reviews"
    ),
    path("payments/<int:movie_id>/", views.payment, name="payments"),
    path("search", views.search, name='search'),
    path(
    "movies/<int:movie_id>/review/",
    views.add_review,
    name="add_review",
    ),
    path(
    "payment-verify/",
    views.payment_success,
    name="payment_success"
    )
]