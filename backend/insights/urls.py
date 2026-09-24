from django.urls import path

from .views import ModelInfoView, SuggestCategoryView

urlpatterns = [
    path("ml/suggest-category/", SuggestCategoryView.as_view(), name="ml-suggest-category"),
    path("ml/info/", ModelInfoView.as_view(), name="ml-info"),
]
