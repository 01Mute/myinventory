from rest_framework import generics, response, viewsets
from rest_framework.decorators import action

from .models import LocationNode
from .serializers import LocationNodeSerializer, LocationNodeTreeSerializer


class LocationNodeViewSet(viewsets.ModelViewSet):
    serializer_class = LocationNodeSerializer

    def get_queryset(self):
        return (
            LocationNode.objects.filter(home__owner=self.request.user)
            .select_related("home", "floor_plan", "parent")
            .prefetch_related("children")
            .order_by("home_id", "floor_plan_id", "path", "sort_order", "id")
        )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk=None):
        node = self.get_object()
        serializer = LocationNodeTreeSerializer(node, context={"request": request})
        return response.Response(serializer.data)


class LocationNodeByFloorPlanView(generics.ListAPIView):
    serializer_class = LocationNodeSerializer

    def get_queryset(self):
        return (
            LocationNode.objects.filter(
                home__owner=self.request.user,
                floor_plan_id=self.kwargs["floor_plan_id"],
            )
            .select_related("home", "floor_plan", "parent")
            .order_by("path", "sort_order", "id")
        )
