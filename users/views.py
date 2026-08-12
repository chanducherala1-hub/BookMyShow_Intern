from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
import random


User = get_user_model()


def register(request):

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        phone_number = request.POST.get("phone_number")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Check passwords match
        if password1 != password2:
            messages.error(
                request,
                "Passwords do not match."
            )
            return redirect("register")

        # Check email already exists
        if User.objects.filter(email=email).exists():
            messages.error(
                request,
                "Email already taken."
            )
            return redirect("register")

        # Check phone number already exists
        if User.objects.filter(phone_number=phone_number).exists():
            messages.error(
                request,
                "Phone number already taken."
            )
            return redirect("register")

        # Generate OTP
        otp = str(random.randint(100000, 999999))

        # Hash password before storing it in session
        password_hash = make_password(password1)

        request.session["pending_user"] = {
            "full_name": full_name,
            "phone_number": phone_number,
            "email": email,
            "password_hash": password_hash,
            "otp": otp,
        }

        subject = "Your BookMyShow Registration OTP"

        message = (
            f"Hi {full_name},\n\n"
            f"Your OTP for registration is: {otp}\n\n"
            f"Do not share this code with anyone."
        )

        try:

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            messages.success(
                request,
                f"An OTP has been sent to {email}."
            )

            return redirect("verify_otp")

        except Exception as e:

            messages.error(
                request,
                f"Failed to send OTP email: {e}"
            )

            return redirect("register")

    return render(
        request,
        "users/register.html"
    )

def verify_otp(request):

    pending_user = request.session.get("pending_user")

    if not pending_user:

        messages.error(
            request,
            "Session expired. Please register again."
        )

        return redirect("register")

    if request.method == "POST":

        entered_otp = request.POST.get("otp")

        if entered_otp == pending_user["otp"]:

            user = User(
                username=pending_user["phone_number"],
                full_name=pending_user["full_name"],
                phone_number=pending_user["phone_number"],
                email=pending_user["email"],
                is_verified=True,
            )

            # Use already-hashed password
            user.password = pending_user["password_hash"]

            user.save()

            del request.session["pending_user"]

            auth.login(request, user)

            messages.success(
                request,
                "Registration successful! Welcome."
            )

            return redirect("/")

        else:

            messages.error(
                request,
                "Invalid OTP. Please try again."
            )

    return render(
        request,
        "users/verify_otp.html",
        {
            "email": pending_user["email"]
        }
    )



def login_view(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        try:

            user = User.objects.get(
                email=email
            )

        except User.DoesNotExist:

            messages.error(
                request,
                "Invalid phone number or email."
            )

            return redirect("login")

        if not user.check_password(password):

            messages.error(
                request,
                "Invalid password."
            )

            return redirect("login")

        if not user.is_active:

            messages.error(
                request,
                "Your account is inactive."
            )

            return redirect("login")

        auth.login(request, user)

        messages.success(
            request,
            "Login successful!"
        )

        return redirect("/")

    return render(request, "users/login.html")



def logout(request):

    auth.logout(request)

    return redirect("/")



@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Verify current password
        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("change_password")

        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect("change_password")

        # Set and save new password directly without validate_password
        request.user.set_password(new_password)
        request.user.save()

        # Keep session active so the user isn't logged out
        auth.update_session_auth_hash(request, request.user)

        messages.success(request, "Password changed successfully!")
        return redirect("/")

    return render(request, "users/change_password.html")


def forgot_password(request):

    if request.method == "POST":

        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:

            messages.error(
                request,
                "No account found with this email."
            )

            return redirect("forgot_password")

        token = default_token_generator.make_token(user)

        uid = urlsafe_base64_encode(
            force_bytes(user.pk)
        )

        # Generate the reset URL automatically
        reset_path = reverse(
            "reset_password",
            kwargs={
                "uidb64": uid,
                "token": token,
            }
        )

        reset_url = request.build_absolute_uri(reset_path)

        subject = "BookMyShow Password Reset"

        message = (
            f"Hi {user.full_name},\n\n"
            f"You requested a password reset.\n\n"
            f"Click the link below to reset your password:\n\n"
            f"{reset_url}\n\n"
            f"If you did not request this, ignore this email."
        )

        try:

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )

            messages.success(
                request,
                "Password reset link has been sent to your email."
            )

            return redirect("login")

        except Exception as e:

            messages.error(
                request,
                f"Failed to send email: {e}"
            )

            return redirect("forgot_password")

    return render(
        request,
        "users/forgot_password.html"
    )

User = get_user_model()


def reset_password(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "Invalid or expired password reset link.")
        return redirect("forgot_password")

    if request.method == "POST":
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Check if either field is empty
        if not password1 or not password2:
            messages.error(request, "Please enter both passwords.")
            return render(request, "users/reset_password.html")

        # Only check if password1 and password2 match
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "users/reset_password.html")

        # Update the password directly (no validation checks)
        user.set_password(password1)
        user.save()

        messages.success(
            request, "Password changed successfully. Please login."
        )
        return redirect("login")

    return render(request, "users/reset_password.html")