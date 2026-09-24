from django.urls import path

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("users/search/", views.UserSearchView.as_view(), name="user-search"),
]
