from rest_framework import serializers
# from django.contrib.auth.models import User
from blog.models import Blog, Comment, Admin, CustomUser
from django.utils.text import slugify
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

    class Meta:
        model = Admin
        fields = ('id', 'user', 'uuid', 'created_at', 'updated_at' , 'work_domain')
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

class BlogSerializer(serializers.ModelSerializer):

    class Meta:
        model = Blog
        fields = ('id', 'title', 'content', 'slug', 'status', 
                 'created_at', 'updated_at', 'published_at' )
        read_only_fields = ('id' ,'created_at', 'updated_at', 'published_at')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            admin = Admin.objects.get(user=request.user)
            validated_data['admin'] = admin
        return super().create(validated_data)

class Blog_List_Serializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    class Meta:
        model = Blog
        fields = ('id', 'title', 'status','slug', 'created_at', 'updated_at', 'content')
    
    def get_content(self, obj):
        # Return first 17 characters of content
        if obj.content:
            return obj.content[:17]
        else:
            return ''

class BlogCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = ('title',)

# class SectionCreateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Section
#         fields = ('title', 'content', 'order', 'section_type')

class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content', 'parent') 