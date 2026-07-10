from django import forms
from django.core.exceptions import ValidationError

from accounts.security import validate_safe_content

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "placeholder": "What's on your mind?"}),
        }

    def clean_content(self):
        content = self.cleaned_data["content"]
        issues = validate_safe_content(content)
        if issues:
            raise ValidationError(issues[0])
        return content


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(attrs={"rows": 2, "placeholder": "Write a comment..."}),
        }

    def clean_content(self):
        content = self.cleaned_data["content"]
        issues = validate_safe_content(content)
        if issues:
            raise ValidationError(issues[0])
        return content
