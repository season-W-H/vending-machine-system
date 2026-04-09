from rest_framework import viewsets
from .models import User
from .serializers import UserSerializer

# 用户视图集
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer