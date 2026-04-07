from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q


class PhoneOrUsernameAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows login with either
    phone number or username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if username is None or password is None:
            return None

        # Try to find user by phone number first, then by username
        try:
            # Check if the input looks like a phone number (all digits)
            if username.isdigit():
                # Try phone lookup first
                from .models import UserProfile
                profile = UserProfile.objects.select_related('user').filter(
                    phone=username
                ).first()
                if profile:
                    user = profile.user
                    if user.check_password(password) and self.user_can_authenticate(user):
                        return user
        except UserProfile.DoesNotExist:
            pass

        # Fall back to username lookup
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserModel.DoesNotExist:
            return None

        return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
