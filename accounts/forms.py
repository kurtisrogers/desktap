from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import ChildInvite, User, UserRole


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "date_of_birth", "password1", "password2")

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise ValidationError(
                "You must be 18 or older to sign up. Children need a parent account."
            )
        return dob

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.date_of_birth = self.cleaned_data["date_of_birth"]
        user.role = UserRole.ADULT
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or email")

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username and password:
            from django.contrib.auth import authenticate

            user = authenticate(
                self.request,
                username=username,
                password=password,
            )
            if user is None:
                user = User.objects.filter(email=username).first()
                if user:
                    user = authenticate(
                        self.request,
                        username=user.username,
                        password=password,
                    )
            if user is None:
                raise ValidationError("Invalid credentials.")
            if user.is_suspended:
                raise ValidationError("This account has been suspended.")
            if user.is_child and hasattr(user, "parent_link") and user.parent_link.child_disabled:
                raise ValidationError("This account has been disabled by a parent.")
            self.confirm_login_allowed(user)
            self.user_cache = user
        return self.cleaned_data


class TotpVerifyForm(forms.Form):
    token = forms.CharField(
        max_length=8,
        label="Authentication code",
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "inputmode": "numeric"}),
    )


class ProfileSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("display_name", "bio")


class AddChildForm(forms.ModelForm):
    class Meta:
        model = ChildInvite
        fields = ("email", "username", "date_of_birth")
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age >= 18:
            raise ValidationError("Child accounts are for users under 18.")
        if age < 13:
            raise ValidationError("Users must be at least 13 years old.")
        return dob

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email


class ChildSetupForm(forms.Form):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise ValidationError("Passwords do not match.")
        return cleaned


class ReportForm(forms.Form):
    REASON_CHOICES = [
        ("spam", "Spam"),
        ("harassment", "Harassment or bullying"),
        ("inappropriate", "Inappropriate content"),
        ("safety", "Safety concern"),
        ("other", "Other"),
    ]
    reason = forms.ChoiceField(choices=REASON_CHOICES)
    details = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        max_length=500,
    )
