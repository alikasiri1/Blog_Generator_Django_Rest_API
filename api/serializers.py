from rest_framework import serializers
# from django.contrib.auth.models import User
from blog.models import Blog, Comment, Admin, CustomUser ,DocumentContent
from django.utils.text import slugify
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# from .models import Admin

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'password', 'first_name' , 'last_name')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user
    


class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Admin
        fields = ('id', 'user', 'uuid', 'created_at', 'updated_at' , 'work_domain', 'image')
        read_only_fields = ('uuid', 'created_at', 'updated_at')

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer().create(user_data)
        admin = Admin.objects.create(user=user, **validated_data)
        return admin
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update user fields
        for attr, value in user_data.items():
            if attr == 'password':
                user.set_password(value)
            else:
                setattr(user, attr, value)
        user.save()

        # Update admin fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    work_domain = serializers.CharField()

    def validate(self, data):
        print(data)
        if CustomUser.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError({"email": "This email is already taken."})

        if CustomUser.objects.filter(username=data["username"]).exists():
            raise serializers.ValidationError({"username": "This username is already taken."})

        if Admin.objects.filter(work_domain=data["work_domain"]).exists():
            raise serializers.ValidationError({"work_domain": "This work domain is already used."})

        return data

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        admin = Admin.objects.create(
            user=user,
            work_domain=validated_data["work_domain"]
        )

        return admin

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"   # this makes JWT use "email" instead of "username"

    def validate(self, attrs):
        print(attrs)
        email = attrs.get("email")
        password = attrs.get("password")

        # authenticate by email
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password")

        data = super().validate(attrs)

        # Add admin info
        try:
            admin = Admin.objects.get(user=user)
            data["work_domain"] = str(admin.work_domain)
            data["admin_uuid"] = str(admin.uuid)
        except Admin.DoesNotExist:
            data["work_domain"] = None
            data["admin_uuid"] = None

        return data

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'content', 'user', 'created_at', 'updated_at', 'replies')
        read_only_fields = ('user',)

    def get_replies(self, obj):
        if obj.parent is None:  # Only get replies for top-level comments
            replies = Comment.objects.filter(parent=obj)
            return CommentSerializer(replies, many=True).data
        return []

class BlogAdminInfoSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)


    class Meta:
        model = Admin
        fields = ('first_name', 'last_name', 'work_domain')
        read_only_fields = fields

class BlogSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    admin_info = BlogAdminInfoSerializer(source='admin', read_only=True)
    class Meta:
        model = Blog
        fields = ('id', 'title', 'content', 'slug', 'status', 
                 'created_at', 'updated_at', 'published_at' , 'image' , 'image_url','settings','admin_info','blog_type')
        read_only_fields = ('id' ,'created_at', 'updated_at', 'published_at')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            admin = Admin.objects.get(user=request.user)
            validated_data['admin'] = admin
        return super().create(validated_data)

class Blog_List_Serializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False, allow_null=True)
    class Meta:
        model = Blog
        fields = ('id', 'title', 'status','slug', 'created_at', 'updated_at', 'content' , 'image', 'image_url' , 'blog_type') 
    
    def get_content(self, obj):
        # Return first 17 characters of content
        if obj.content:
            return obj.content[:100]
        else:
            return ''

class BlogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ('title',)


class DocumentContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentContent
        fields = '__all__'

class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content', 'parent') 