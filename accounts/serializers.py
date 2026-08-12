from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "full_name", "staff_id", "email", "phone",
            "role", "role_label", "home_region_id", "must_change_password",
            "active", "last_login_at", "created_at",
        )
        read_only_fields = fields


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "full_name", "staff_id", "email", "phone",
            "role", "home_region_id", "must_change_password", "active", "password",
        )
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password", None) or User.objects.make_random_password()
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
            instance.must_change_password = True
            instance.session_version += 1
        instance.save()
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
