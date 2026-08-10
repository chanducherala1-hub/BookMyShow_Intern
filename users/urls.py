from django.urls import path

from . import views


urlpatterns = [

    # Registration
    path(
        "register/",
        views.register,
        name="register"
    ),

    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp"
    ),

    # Login
    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout,
        name="logout"
    ),

    # Change password
    path(
        "change-password/",
        views.change_password,
        name="change_password"
    ),

    # Forgot password
    path(
        "forgot-password/",
        views.forgot_password,
        name="forgot_password"
    ),

    # Reset password
    path(
        "reset-password/<uidb64>/<token>/",
        views.reset_password,
        name="reset_password"
    ),
]