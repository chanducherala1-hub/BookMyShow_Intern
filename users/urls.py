from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("login/",views.login_view,name="login"),
    path("logout/",views.logout,name="logout")
]