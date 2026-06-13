from rest_framework import viewsets

from .models import FloorPlan, Home
from .serializers import FloorPlanSerializer, HomeSerializer


class HomeViewSet(viewsets.ModelViewSet):
    serializer_class = HomeSerializer

    def get_queryset(self):
        return Home.objects.filter(owner=self.request.user).order_by("name", "id")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class FloorPlanViewSet(viewsets.ModelViewSet):
    serializer_class = FloorPlanSerializer

    def get_queryset(self):
        return (
            FloorPlan.objects.filter(home__owner=self.request.user)
            .select_related("home")
            .order_by("home__name", "name", "id")
        )
