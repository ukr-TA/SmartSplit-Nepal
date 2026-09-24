import re

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .models import User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSummarySerializer,
    normalize_phone,
)


class AuthThrottle(AnonRateThrottle):
    rate = "30/minute"


def auth_payload(user, request):
    token, _ = Token.objects.get_or_create(user=user)
    return {
        "token": token.key,
        "user": ProfileSerializer(user, context={"request": request}).data,
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(auth_payload(user, request), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(auth_payload(serializer.validated_data["user"], request))


class LogoutView(APIView):
    def post(self, request):
        # Deleting the token invalidates it on the server
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch", "options"]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        # rotate the token so other sessions are logged out
        Token.objects.filter(user=request.user).delete()
        return Response(auth_payload(request.user, request))


class UserSearchView(APIView):
    """
    Find registered users to add to a group.

    - Full 10-digit phone number -> exact match (phone shown masked).
    - Email -> exact match only (emails are never listed by partial search).
    - Name  -> partial match, at least 2 characters.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        users = User.objects.none()
        match_type = None
        compact = re.sub(r"[\s\-+()]", "", query)

        if "@" in query:
            users = User.objects.filter(email__iexact=query)
            match_type = "email"
        elif compact.isdigit():
            # Phone numbers only match in full, so numbers can't be enumerated
            digits = normalize_phone(compact)
            if len(digits) == 10:
                users = User.objects.filter(phone_number=digits)
            match_type = "phone"
        elif len(query) >= 2:
            users = User.objects.filter(
                Q(full_name__icontains=query)
            )
            match_type = "name"

        users = users.filter(is_active=True).exclude(pk=request.user.pk).order_by("full_name")[:10]
        data = UserSummarySerializer(users, many=True, context={"request": request}).data
        return Response({"match_type": match_type, "results": data})
