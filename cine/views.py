from django.shortcuts import render,get_object_or_404,redirect
from .models import Movie, Theater, Show,MovieImage,Screen,Booking,Seat,Review,SeatLock,Order
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
import razorpay
from django.conf import settings
import qrcode
import io
import base64
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.core.mail import EmailMessage

client=razorpay.Client(auth=(settings.RAZORPAY_KEY_ID,settings.RAZORPAY_KEY_SECRET))

def index(request):
    movies = Movie.objects.all()
    return render(request, "index.html", {"movies": movies})


def details(request, movie_id):

    movie = get_object_or_404(
        Movie,
        id=movie_id
    )

    similar_movies = Movie.objects.filter(

        genres__in=movie.genres.all(),

        languages__in=movie.languages.all()

    ).exclude(

        id=movie.id

    ).distinct()[:6]

    return render(

        request,

        "details.html",

        {

            "movie": movie,

            "similar_movies": similar_movies

        }
    )

def books(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    Show.objects.filter(
        show_date__lt=timezone.localdate()
    ).delete()

    selected_date = request.GET.get("date")

    shows = Show.objects.none()

    if selected_date:
        shows = Show.objects.filter(
            movie=movie,
            show_date=selected_date
        ).select_related(
            "screen__theater"
        )

    available_dates = Show.objects.filter(
        movie=movie,
        show_date__gte=timezone.localdate()
    ).values("show_date").distinct().order_by("show_date")

    grouped_shows = defaultdict(list)

    for show in shows:
        grouped_shows[show.screen.theater].append(show)

    return render(request, "books.html", {
        "movie": movie,
        "available_dates": available_dates,
        "grouped_shows": grouped_shows.items(),
    })

from django.utils import timezone

@login_required
def seats(request, show_id):

    show = get_object_or_404(Show, id=show_id)

    # Remove expired locks
    SeatLock.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()

    seats = Seat.objects.filter(
        screen=show.screen
    ).order_by("seat_number")

    # Show locks of OTHER users only
    locked_seat_ids = list(

        SeatLock.objects.filter(

            show=show,

            expires_at__gt=timezone.now(),

            is_active=True

        ).exclude(

            user=request.user

        ).values_list(
            "seat_id",
            flat=True
        )

    )

    booked_seat_ids = list(

        Booking.objects.filter(

            show=show,

            payment_status="Success"

        ).values_list(
            "seats__id",
            flat=True
        )

    )

    return render(request,"seats.html",{

        "show":show,

        "seats":seats,

        "locked_seat_ids":locked_seat_ids,

        "booked_seat_ids":booked_seat_ids,

    })
def book_seats(request, show_id):

    if request.method == "POST":

        ids = request.POST.get("seats").split(",")

        booking = Booking.objects.create(
            user=request.user,
            show_id=show_id,
            total_amount=0
        )
        request.session["booking_id"] = booking.id
        request.session.modified = True
        for seat_id in ids:
            seat = Seat.objects.get(id=seat_id)
            seat.is_booked = True
            seat.save()
            booking.seats.add(seat)

        return redirect(
        "payments",
        movie_id=booking.show.movie.id
    )

@login_required
def add_review(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    booking = Booking.objects.filter(
        user=request.user,
        show__movie=movie,
        booking_status="Confirmed",
        payment_status="Success"
    ).first()

    if not booking:
        return render(request, "error.html", {
            "message": "You can review only after booking this movie."
        })

    show = booking.show

    show_end_time = datetime.combine(
        show.show_date,
        show.show_time
    ) + timedelta(minutes=movie.duration_minutes)

    show_end_time = timezone.make_aware(show_end_time)

    if timezone.now() < show_end_time:
        return render(request, "error.html", {
            "message": "You can review only after the show has completed."
        })

    if Review.objects.filter(
        user=request.user,
        booking=booking
    ).exists():
        return render(request, "error.html", {
            "message": "You have already reviewed this movie."
        })

    if request.method == "POST":

        rating = request.POST.get("rating")
        review = request.POST.get("review")

        Review.objects.create(
            movie=movie,
            user=request.user,
            booking=booking,
            rating=rating,
            review=review,
            verified_viewer=True
        )

        return redirect(
            "details",
            movie_id=movie.id
        )

    return render(request, "add_review.html", {
        "movie": movie
    })


@login_required
def lock_seats(request, show_id):

    if request.method != "POST":
        return HttpResponse("Invalid Request")

    show = get_object_or_404(Show,id=show_id)

    selected = request.POST.get("selected_seats","")

    if not selected:
        return HttpResponse("No seats selected")

    seat_numbers = [x.strip() for x in selected.split(",")]

    request.session["show_id"] = show.id
    request.session["selected_seats"] = seat_numbers

    # Remove old locks of this user
    SeatLock.objects.filter(

        user=request.user,

        show=show,

        is_active=True

    ).delete()

    booking, created = Booking.objects.get_or_create(

        user=request.user,

        show=show,

        payment_status="Pending",

        defaults={
            "total_amount":0
        }

    )

    booking.seats.clear()

    for seat_number in seat_numbers:

        seat = get_object_or_404(

            Seat,

            seat_number=seat_number,

            screen=show.screen

        )

        # Check lock from OTHER users
        locked = SeatLock.objects.filter(

            show=show,

            seat=seat,

            expires_at__gt=timezone.now(),

            is_active=True

        ).exclude(

            user=request.user

        ).exists()

        if locked:

            return HttpResponse(
                f"{seat.seat_number} already locked"
            )

        SeatLock.objects.create(

            user=request.user,

            show=show,

            seat=seat,

            locked_at=timezone.now(),

            expires_at=timezone.now()+timedelta(minutes=2),

            is_active=True

        )

        booking.seats.add(seat)

    request.session["booking_id"]=booking.id

    return redirect(

        "payments",

        movie_id=show.movie.id

    )

@login_required
def payment(request, movie_id):
    Order.objects.filter(
        payment_status="Pending",
        created_at__lt=timezone.now() - timedelta(minutes=10)
    ).delete()
    print(settings.RAZORPAY_KEY_ID)
    print(settings.RAZORPAY_KEY_SECRET)

    show_id = request.session.get("show_id")

    if not show_id:
        return HttpResponse("Show ID not found")
    print(request.session.items())
    booking_id = request.session.get("booking_id")

    if not booking_id:
        return HttpResponse("Booking ID not found")

    booking = get_object_or_404(
        Booking,
        id=booking_id
    )

    show = get_object_or_404(
        Show,
        id=show_id
    )

    movie = show.movie

    selected_seats = request.session.get(
        "selected_seats",
        []
    )

    amount = len(selected_seats) * show.ticket_price

    razorpay_order = client.order.create({

        "amount": int(amount * 100),

        "currency": "INR",

        "payment_capture": 1

    })
    print(razorpay_order)

    order = Order.objects.create(

        user=request.user,

        booking=booking,

        amount=amount,

        razorpay_order_id=razorpay_order["id"]


    )

    context = {

        "movie": movie,

        "show": show,

        "selected_seats": selected_seats,

        "amount": amount,

        "order_id": razorpay_order["id"],

        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_callback_url": settings.RAZORPAY_CALLBACK_URL,

    }

    return render(
        request,
        "payment.html",
        context
    )

import json

@csrf_exempt
def payment_success(request):

    payment_id = request.POST.get(
        "razorpay_payment_id"
    )

    order_id = request.POST.get(
        "razorpay_order_id"
    )

    signature = request.POST.get(
        "razorpay_signature"
    )
    print(payment_id)
    print(order_id)
    print(signature)
    
    order = get_object_or_404(
        Order,
        razorpay_order_id=order_id
    )

    order.razorpay_payment_id = payment_id
    order.razorpay_signature = signature
    order.payment_status = "Success"
    order.save()

    booking = order.booking

    booking.payment_status = "Success"
    booking.booking_status = "Confirmed"
    booking.total_amount = order.amount
    booking.save()
    SeatLock.objects.filter(

        user=request.user,

        show=booking.show

    ).delete()
    for seat in booking.seats.all():
        seat.is_booked = True
        seat.save()
    print(booking.seats.all())
    for seat in booking.seats.all():

        seat.is_booked = True

        seat.save()
    booked_seats = booking.seats.all()
    seat_numbers = ", ".join([s.seat_number for s in booking.seats.all()])
    qr_data = (
        f" QR Details\n"
        f"Booking ID: {booking.id}\n"
        f"Payment ID: {payment_id}\n"
        f"Movie: {booking.show.movie.title}\n"
        f"Theater: {booking.show.screen.theater.theater_name}\n"
        f"City: {booking.show.screen.theater.city}\n"
        f"Screen: {booking.show.screen.screen_number} ({booking.show.screen.screen_type})\n"
        f"Date & Time: {booking.show.show_date} | {booking.show.show_time}\n"
        f"Seats: {seat_numbers}\n"
    )
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    context = {
        "order": order, 
        "booking": booking,
        "movie": booking.show.movie,       
        "show": booking.show,            
        "seats": booking.seats.all(), 
        "qr_code": qr_code_base64,
    }
    try:
        html_string = render_to_string("ticket_pdf.html", context)
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(html_string, dest=pdf_file)

        if not pisa_status.err:
            email_subject = f"Your Ticket Confirmation - {booking.show.movie.title}"
            email_body = f"Hi {request.user.username},\n\nThank you for your booking! Please find attached your ticket PDF with QR code."
            recipient_email = request.user.email

            if recipient_email:
                email = EmailMessage(
                    subject=email_subject,
                    body=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email],
                )
                email.attach(f"Ticket_# {booking.id}.pdf", pdf_file.getvalue(), "application/pdf")
                email.send(fail_silently=True)
    except Exception as e:
        print(f"Failed to send email: {e}")
    return render(request, "payment-verify.html",context)

def search(request):
    search = request.GET.get('search', '')

    allposts = Movie.objects.filter(
        title__icontains=search
    )

    params = {
        'allposts': allposts,
        'search': search,
    }

    return render(
        request,
        'search.html',
        params
    )


@login_required
def edit_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id,
        user=request.user
    )

    if request.method == "POST":

        review.rating = request.POST.get("rating")
        review.review = request.POST.get("review")

        review.save()

        return redirect(
            "details",
            movie_id=review.movie.id
        )

    return render(
        request,
        "edit_review.html",
        {
            "review": review
        }
    )

@login_required
def report_review(request, review_id):

    review = get_object_or_404(
        Review,
        id=review_id
    )

    review.is_reported = True

    review.save()

    return redirect(
        "details",
        movie_id=review.movie.id
    )



client = razorpay.Client(
    auth=(
        settings.RAZORPAY_KEY_ID,
        settings.RAZORPAY_KEY_SECRET
    )
)


def show_reviews(request, movie_id):

    movie = get_object_or_404(Movie, id=movie_id)

    reviews = Review.objects.filter(
        movie=movie
    ).select_related("user").order_by("-id")

    return render(
        request,
        "show_reviews.html",
        {
            "movie": movie,
            "reviews": reviews
        }
    )