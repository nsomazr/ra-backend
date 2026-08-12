from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("username",)
    list_display = ("username", "full_name", "role", "active", "must_change_password", "last_login_at")
    list_filter = ("role", "active", "must_change_password")
    search_fields = ("username", "full_name", "email", "staff_id")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Profile", {"fields": ("full_name", "staff_id", "email", "phone", "role", "home_region_id")}),
        ("Security", {"fields": ("must_change_password", "failed_attempts", "locked_until", "session_version", "active", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "password1", "password2", "role", "is_staff", "is_superuser"),
        }),
    )
