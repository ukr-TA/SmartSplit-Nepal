from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User, nepal_phone_validator

MAX_PICTURE_BYTES = 3 * 1024 * 1024  # 3 MB


def normalize_phone(value):
    """Accept '+977 98-1234 5678' style input and keep only the 10 local digits."""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if digits.startswith("977") and len(digits) == 13:
        digits = digits[3:]
    return digits


def mask_phone(phone):
    """98XXXX5678 - enough to recognise a friend without exposing the full number."""
    if not phone or len(phone) < 6:
        return phone
    return f"{phone[:2]}XXXX{phone[-4:]}"


def picture_url(request, user):
    if not user.profile_picture:
        return None
    url = user.profile_picture.url
    return request.build_absolute_uri(url) if request else url


class UserSummarySerializer(serializers.ModelSerializer):
    """Public view of another user: no email, masked phone."""

    phone_number = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "phone_number", "profile_picture"]

    def get_phone_number(self, obj):
        return mask_phone(obj.phone_number)

    def get_profile_picture(self, obj):
        return picture_url(self.context.get("request"), obj)


class ProfileSerializer(serializers.ModelSerializer):
    """The logged-in user's own full profile."""

    profile_picture = serializers.ImageField(required=False, allow_null=True)
    # longer than 10 so "+977 98-1234-5678" can be accepted and normalised
    phone_number = serializers.CharField(max_length=20)
    remove_picture = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "full_name", "email", "phone_number",
            "profile_picture", "remove_picture", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["profile_picture"] = picture_url(self.context.get("request"), instance)
        return data

    def validate_full_name(self, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise serializers.ValidationError("Please enter your full name.")
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_phone_number(self, value):
        value = normalize_phone(value)
        try:
            nepal_phone_validator(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        qs = User.objects.filter(phone_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This phone number is already registered.")
        return value

    def validate_profile_picture(self, value):
        if value and value.size > MAX_PICTURE_BYTES:
            raise serializers.ValidationError("Profile picture must be smaller than 3 MB.")
        return value

    def update(self, instance, validated_data):
        remove = validated_data.pop("remove_picture", False)
        new_picture = validated_data.pop("profile_picture", None)
        if (remove or new_picture) and instance.profile_picture:
            instance.profile_picture.delete(save=False)
            instance.profile_picture = None
        if new_picture:
            instance.profile_picture = new_picture
        return super().update(instance, validated_data)


class RegisterSerializer(ProfileSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    class Meta(ProfileSerializer.Meta):
        fields = ["id", "full_name", "email", "phone_number", "password"]

    def validate(self, attrs):
        user = User(
            full_name=attrs.get("full_name"),
            email=attrs.get("email"),
            phone_number=attrs.get("phone_number"),
        )
        try:
            password_validation.validate_password(attrs["password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """Log in with email OR Nepali phone number + password."""

    identifier = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        email = identifier.lower()
        if "@" not in identifier:
            match = User.objects.filter(phone_number=normalize_phone(identifier)).first()
            email = match.email if match else None

        user = None
        if email:
            user = authenticate(
                request=self.context.get("request"), username=email, password=attrs["password"]
            )
        if not user:
            raise serializers.ValidationError("Incorrect email/phone or password.")
        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value, self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value
