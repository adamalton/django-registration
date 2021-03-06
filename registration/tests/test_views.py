from django.core.urlresolvers import reverse
from django.test import override_settings, TestCase

from ..models import RegistrationProfile


@override_settings(ROOT_URLCONF='registration.tests.urls')
class ActivationViewTests(TestCase):
    @override_settings(ACCOUNT_ACTIVATION_DAYS=7)
    def test_activation(self):
        """
        Activation of an account functions properly when using a
        simple string URL as the success redirect.

        """
        data = {
            'username': 'bob',
            'email': 'bob@example.com',
            'password1': 'secret',
            'password2': 'secret'
        }
        resp = self.client.post(reverse('registration_register'),
                                data=data)

        profile = RegistrationProfile.objects.get(
            user__username=data['username']
        )

        resp = self.client.get(reverse(
            'registration_activate',
            args=(),
            kwargs={'activation_key': profile.activation_key})
        )
        self.assertRedirects(resp, '/')
