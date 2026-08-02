from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib import auth
from django.contrib.auth import get_user_model
import random
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

def register(request):
    if request.method == "POST":
        full_name = request.POST["full_name"]
        phonenumber = request.POST["phone_number"]
        email = request.POST["email"]
        password1 = request.POST["password1"]
        password2 = request.POST["password2"]

        if password1 == password2:

            if User.objects.filter(email=email).exists():
                messages.info(request, "Email already taken")
                return redirect("register")

            elif User.objects.filter(phone_number=phonenumber).exists():
                messages.info(request, "Phone Number already taken")
                return redirect("register")

            else:
                otp = str(random.randint(100000, 999999))

                request.session["pending_user"] = {
                    "full_name": full_name,
                    "phone_number": phonenumber,
                    "email": email,
                    "password": password1,
                    "otp": otp,
                }
                subject = "Your BookMyShow Registration OTP"
                message = f"Hi {full_name},\n\nYour OTP for registration is: {otp}\n\nDo not share this code with anyone."

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    messages.success(request, f"An OTP has been sent to {email}.")
                    return redirect("verify_otp")
                except Exception as e:
                    messages.error(request, f"Failed to send OTP email: {e}")
                    return redirect("register")

        else:
            messages.info(request, "Passwords do not match")
            return redirect("register")

    return render(request, "users/register.html")
User = get_user_model()

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if "send_otp" in request.POST:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, "No account found with this email.")
                return redirect("login")

            otp = str(random.randint(100000, 999999))
            request.session["login_otp"] = {
                "email": email,
                "otp": otp,
                "user_id": user.pk,
            }
            subject = "Your Login OTP"
            message = f"Hi {user.full_name},\n\nYour OTP for logging in is: {otp}"

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, f"OTP sent to {email}")
                return render(request, "users/login.html", {"otp_sent": True, "email": email})
            except Exception as e:
                messages.error(request, f"Failed to send email: {e}")
                return redirect("login")

        # CASE 2: User submitted the OTP
        elif "verify_otp" in request.POST:
            entered_otp = request.POST.get("otp")
            session_data = request.session.get("login_otp")

            # FIX WAS HERE: .get() instead of .GET()
            if not session_data or session_data.get("email") != email:
                messages.error(request, "Session expired. Please request a new OTP.")
                return redirect("login")

            if entered_otp == session_data["otp"]:
                user = User.objects.get(pk=session_data["user_id"])
                auth.login(request, user)
                del request.session["login_otp"]

                messages.success(request, "Login Successful!")
                return redirect("/")
            else:
                messages.error(request, "Invalid OTP. Please try again.")
                return render(request, "users/login.html", {"otp_sent": True, "email": email})

    return render(request, "users/login.html", {"otp_sent": False})


def logout(request):
    auth.logout(request)
    return redirect('/')

def verify_otp(request):
    pending_user = request.session.get("pending_user")

    if not pending_user:
        messages.error(request, "Session expired or invalid request. Please register again.")
        return redirect("register")

    if request.method == "POST":
        entered_otp = request.POST.get("otp")

        if entered_otp == pending_user["otp"]:
            user = User.objects.create_user(
                username=pending_user["phone_number"],
                full_name=pending_user["full_name"],
                phone_number=pending_user["phone_number"],
                email=pending_user["email"],
                password=pending_user["password"],
            )
            user.save()

            del request.session["pending_user"]

            auth.login(request, user)
            messages.success(request, "Registration Successful! Welcome.")
            return redirect("/")
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "users/verify_otp.html", {"email": pending_user["email"]})