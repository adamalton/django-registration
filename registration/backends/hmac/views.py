"""
A two-step (registration followed by activation) workflow, implemented
by emailing an HMAC-verified timestamped activation token to the user
on signup.

"""
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.requests import RequestSite
from django.contrib.sites.models import Site
from django.core import signing
from django.template.loader import render_to_string

from registration import signals
from registration.views import ActivationView as BaseActivationView
from registration.views import RegistrationView as BaseRegistrationView


REGISTRATION_SALT = getattr(settings, 'REGISTRATION_SALT', 'registration')


class RegistrationView(BaseRegistrationView):
    """
    Register a new (inactive) user account, generate an activation key
    and email it to the user.

    This is different from the model-based activation workflow in that
    the activation key is simply the username, signed using Django's
    TimestampSigner, with HMAC verification on activation.

    """
    email_body_template = 'registration/activation_email.txt'
    email_subject_template = 'registration/activation_email_subject.txt'

    def register(self, **cleaned_data):
        new_user = self.create_inactive_user(
            **self.get_user_kwargs(**cleaned_data)
        )
        signals.user_registered.send(sender=self.__class__,
                                     user=new_user,
                                     request=self.request)
        return new_user

    def get_success_url(self, user):
        return ('registration_complete', (), {})

    def create_inactive_user(self, **user_kwargs):
        """
        Create the inactive user account and send an email containing
        activation instructions.

        """
        User = get_user_model()
        new_user = User.objects.create_user(**user_kwargs)
        new_user.is_active = False
        new_user.save()

        self.send_activation_email(new_user)

        return new_user

    def get_activation_key(self, user):
        """
        Generate the activation key which will be emailed to the user.

        """
        signer = signing.TimestampSigner(salt=REGISTRATION_SALT)
        activation_key = signer.sign(
            str(getattr(user, user.USERNAME_FIELD))
        )
        return activation_key

    def get_email_context(self, activation_key):
        """
        Build the template context used for the activation email.

        """
        if apps.is_installed('django.contrib.sites'):
            site = Site.objects.get_current()
        else:
            site = RequestSite(self.request)

        return {
            'activation_key': activation_key,
            'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
            'site': site,
        }

    def send_activation_email(self, user):
        """
        Send the activation email. The activation key is simply the
        username, signed using TimestampSigner.

        """
        activation_key = self.get_activation_key(user)
        context = self.get_email_context(activation_key)
        subject = render_to_string(self.email_subject_template,
                                   context)
        # Force subject to a single line to avoid header-injection
        # issues.
        subject = ''.join(subject.splitlines())
        message = render_to_string(self.email_body_template,
                                   context)
        user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)


class ActivationView(BaseActivationView):
    """
    Given a valid activation key, activate the user's
    account. Otherwise, show an error message stating the account
    couldn't be activated.

    """
    def activate(self, *args, **kwargs):
        username = self.validate_key(kwargs.get('activation_key'))
        if username is not None:
            user = self.get_user(username)
            if user is not None:
                user.is_active = True
                user.save()
                return user
        return False

    def get_success_url(self, user):
        return ('registration_activation_complete', (), {})

    def validate_key(self, activation_key):
        """
        Verify that the activation key is valid and within the
        permitted activation time window, returning the username if
        valid or ``None`` if not.

        """
        signer = signing.TimestampSigner(salt=REGISTRATION_SALT)
        try:
            username = signer.unsign(
                activation_key,
                max_age=settings.ACCOUNT_ACTIVATION_DAYS * 86400
            )
            return username
        # SignatureExpired is a subclass of BadSignature, so this will
        # catch either one.
        except signing.BadSignature:
            return None

    def get_user(self, username):
        """
        Given the verified username, look up and return the
        corresponding user account if it exists, or ``None`` if it
        doesn't.

        """
        User = get_user_model()
        lookup_kwargs = {
            User.USERNAME_FIELD: username,
            'is_active': False
        }
        try:
            user = User.objects.get(**lookup_kwargs)
            return user
        except User.DoesNotExist:
            return None
