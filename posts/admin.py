from django.contrib import admin

from .models import Comment, Follow, Post

admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Follow)
