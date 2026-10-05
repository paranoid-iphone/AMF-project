from django.urls import path

from projects.views import (
    ProjectActivateView,
    ProjectCollectionView,
    ProjectDeactivateView,
    ProjectDetailView,
)

urlpatterns = [
    path("", ProjectCollectionView.as_view(), name="project-list"),
    path("<str:id>/", ProjectDetailView.as_view(), name="project-detail"),
    path("<str:id>/activate/", ProjectActivateView.as_view(), name="project-activate"),
    path("<str:id>/deactivate/", ProjectDeactivateView.as_view(), name="project-deactivate"),
]
