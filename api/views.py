# Create your views here.
from rest_framework import viewsets, status

from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from blog.models import  Comment,Admin,CustomUser

from .serializers import CommentSerializer , RegisterSerializer , EmailTokenObtainPairSerializer

from .serializers import AdminSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

# class AdminViewSet(viewsets.ModelViewSet):
#     queryset = Admin.objects.all()
#     serializer_class = AdminSerializer
#     permission_classes = [IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser, JSONParser]
#     lookup_field = 'slug'          #  important
#     lookup_url_kwarg = 'slug'      #  optional but recommended

#     def get_permissions(self):
#         if self.action in ['register', 'profile']:
#             return [AllowAny()]
#         return [IsAuthenticated()]

#     def get_queryset(self):
#         return Admin.objects.filter(user=self.request.user)

#     @action(detail=False, methods=['post'], permission_classes=[AllowAny])
#     def register(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         if serializer.is_valid():
#             admin = serializer.save()
#             return Response(AdminSerializer(admin).data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#     @action(detail=True, methods=['get'], permission_classes=[AllowAny])
#     def profile(self, request, slug=None):
#         admin = self.get_object()
#         serializer = self.get_serializer(admin)
#         return Response(serializer.data)

#     @action(detail=False, methods=['patch']) 
#     def updates(self, request):
#         """
#         PATCH /api/admins/profile/
#         Updates the admin's profile and user fields.
#         """
#         admin = Admin.objects.get(user=request.user) 
#         print(admin)
#         serializer = self.get_serializer(admin, data=request.data, partial=True)

#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminViewSet(viewsets.ModelViewSet):
    serializer_class = AdminSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    lookup_field = 'work_domain'
    lookup_url_kwarg = 'work_domain'

    def get_permissions(self):
        if self.action in ['register', 'profile']:
            return [AllowAny()]
        return [IsAuthenticated()]


    def get_queryset(self):
        if self.action == 'profile':
            return Admin.objects.all()
        return Admin.objects.filter(user=self.request.user)


    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = serializer.save()
        return Response(AdminSerializer(admin).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def profile(self, request, work_domain=None):
        admin = self.get_object()
        serializer = self.get_serializer(admin)
        return Response(serializer.data)


    @action(detail=False, methods=['patch'])
    def updates(self, request):
        admin = Admin.objects.get(user=request.user)
        serializer = self.get_serializer(admin, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# class CommentViewSet(viewsets.ModelViewSet):
#     serializer_class = CommentSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         admin_uuid = self.kwargs.get('admin_uuid')
#         admin = get_object_or_404(Admin, uuid=admin_uuid)
        
#         # Ensure the authenticated user is the admin
#         if admin.user != self.request.user:
#             return Comment.objects.none()
            
#         return Comment.objects.filter(section__blog__admin=admin)

#     def perform_create(self, serializer):
#         section_id = self.request.data.get('section')
#         section = get_object_or_404(Section, id=section_id)
#         serializer.save(user=self.request.user, section=section) 

# class CustomTokenObtainPairView(TokenObtainPairView):
#     def post(self, request, *args, **kwargs):
#         response = super().post(request, *args, **kwargs)
#         print(request.data)
#         # Get username from request data
#         username = request.data.get('username')
        
#         # Get the user from the username
#         try:
#             user = CustomUser.objects.get(username=username)
#             admin = Admin.objects.get(user=user) 
#             # Add admin work_domain to the response
#             response.data['work_domain'] = str(admin.work_domain)
#             response.data['admin_uuid'] = str(admin.uuid)
#         except (CustomUser.DoesNotExist, Admin.DoesNotExist):
#             response.data['work_domain'] = None
#             response.data['admin_uuid'] = None
            
#         return response 

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer