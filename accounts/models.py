import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username.strip(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", User.Role.ADMIN)
        extra.setdefault("must_change_password", False)
        return self.create_user(username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        TEAM_LEADER = "TEAM_LEADER", "Team Leader / Senior MEL Specialist"
        AUDITOR = "AUDITOR", "Inclusive Education Specialist"
        DISABILITY_INCLUSION = "DISABILITY_INCLUSION", "Disability Inclusion Expert"
        FINANCE_COMPLIANCE = "FINANCE_COMPLIANCE", "Financial and Compliance Auditor"
        PROCUREMENT = "PROCUREMENT", "Procurement and Asset Verification Specialist"
        RESEARCH_ASSOCIATE = "RESEARCH_ASSOCIATE", "Research Associate"
        DATA_ANALYST = "DATA_ANALYST", "Data Analyst"
        SAFEGUARDING_LEAD = "SAFEGUARDING_LEAD", "Safeguarding Lead"
        ADMIN = "ADMIN", "System Administrator"
        CBM_VIEWER = "CBM_VIEWER", "CBM Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    staff_id = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.AUDITOR)
    home_region_id = models.CharField(max_length=32, blank=True)
    must_change_password = models.BooleanField(default=True)
    failed_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    session_version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.username

    @property
    def is_active(self):
        return self.active

    @is_active.setter
    def is_active(self, value):
        self.active = value
