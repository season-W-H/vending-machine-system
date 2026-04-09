from rest_framework import viewsets
from .models import Inventory
from .serializers import InventorySerializer

# 库存视图集
class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer