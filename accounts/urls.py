from django.urls import path

from .views import (
    ChangePasswordView,
    HealthView,
    LoginView,
    MeView,
    UserDetailView,
    UserListCreateView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("users/", UserListCreateView.as_view(), name="user-list"),
    path("users/<uuid:id>/", UserDetailView.as_view(), name="user-detail"),
]
