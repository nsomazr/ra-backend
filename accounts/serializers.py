from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from assessment.models import School, SchoolAssignment

User = get_user_model()

ROLE_LABEL_TO_CODE = {label: code for code, label in User.Role.choices}
ROLE_CODE_TO_LABEL = {code: label for code, label in User.Role.choices}


class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    assigned_school_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "full_name", "staff_id", "email", "phone",
            "role", "role_label", "home_region_id", "must_change_password",
            "active", "last_login_at", "created_at", "assigned_school_ids",
        )
        read_only_fields = fields

    def get_assigned_school_ids(self, obj):
        return list(
            SchoolAssignment.objects.filter(user=obj, active=True)
            .values_list("school_id", flat=True)
        )


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.CharField(required=False, allow_blank=True)
    home_region_id = serializers.CharField(required=False, allow_blank=True)
    assigned_school_ids = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True, allow_empty=True,
    )

    class Meta:
        model = User
        fields = (
            "id", "username", "full_name", "staff_id", "email", "phone",
            "role", "home_region_id", "must_change_password", "active", "password",
            "assigned_school_ids",
        )
        read_only_fields = ("id",)

    def validate_role(self, value):
        if not value:
            return User.Role.AUDITOR
        if value in ROLE_CODE_TO_LABEL:
            return value
        if value in ROLE_LABEL_TO_CODE:
            return ROLE_LABEL_TO_CODE[value]
        raise serializers.ValidationError(f"Unknown role: {value}")

    def validate_home_region_id(self, value):
        if not value or str(value).upper() in ("ALL", ""):
            return ""
        text = str(value).strip()
        from assessment.models import Region
        region = Region.objects.filter(region_id__iexact=text).first()
        if region:
            return region.region_id
        region = Region.objects.filter(region_name__iexact=text).first()
        if region:
            return region.region_id
        return text.upper()

    def _sync_assignments(self, user, school_ids):
        if school_ids is None:
            return
        wanted = set(str(s) for s in school_ids if s)
        existing = {
            a.school_id: a
            for a in SchoolAssignment.objects.filter(user=user)
        }
        for school_id, assignment in existing.items():
            if school_id not in wanted and assignment.active:
                assignment.active = False
                assignment.save(update_fields=["active"])
        for school_id in wanted:
            if not School.objects.filter(pk=school_id).exists():
                continue
            assignment = existing.get(school_id)
            if assignment:
                if not assignment.active:
                    assignment.active = True
                    assignment.save(update_fields=["active"])
            else:
                SchoolAssignment.objects.create(
                    school_id=school_id,
                    user=user,
                    assignment_role=user.role or "AUDITOR",
                    active=True,
                )

    def create(self, validated_data):
        school_ids = validated_data.pop("assigned_school_ids", None)
        password = validated_data.pop("password", None) or User.objects.make_random_password()
        role = validated_data.get("role")
        if role == User.Role.ADMIN:
            validated_data.setdefault("is_staff", True)
        validated_data.setdefault("must_change_password", True)
        user = User.objects.create_user(password=password, **validated_data)
        self._sync_assignments(user, school_ids)
        return user

    def update(self, instance, validated_data):
        school_ids = validated_data.pop("assigned_school_ids", None)
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if instance.role == User.Role.ADMIN:
            instance.is_staff = True
        if password:
            instance.set_password(password)
            instance.must_change_password = True
            instance.session_version += 1
        instance.save()
        self._sync_assignments(instance, school_ids)
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        if not user.active:
            raise serializers.ValidationError("Account is inactive.")
        if user.locked_until and user.locked_until > timezone.now():
            raise serializers.ValidationError("Account is temporarily locked.")
        user.failed_attempts = 0
        user.last_login_at = timezone.now()
        user.save(update_fields=["failed_attempts", "last_login_at"])
        data["user"] = UserSerializer(user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, allow_blank=True)
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        current = attrs.get("current_password") or ""
        if not user.must_change_password and not user.check_password(current):
            raise serializers.ValidationError({"current_password": "Incorrect current password."})
        if user.must_change_password and current and not user.check_password(current):
            raise serializers.ValidationError({"current_password": "Incorrect current password."})
        return attrs
