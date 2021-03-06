"""
URLconf for registration and activation, using django-registration's
HMAC activation workflow.

"""


from django.conf.urls import include, url
from django.views.generic.base import TemplateView

from .views import ActivationView, RegistrationView


urlpatterns = [
    url(r'^activate/complete/$',
        TemplateView.as_view(
            template_name='registration/activation_complete.html'
        ),
        name='registration_activation_complete'),
    # This URL pattern needs to match anything legal in a username and
    # anything legal in a Django-produced HMAC-signed token. That's
    # all word characters, the dot, the at-sign, the plus sign, the
    # hyphen and the colon.
    url(r'^activate/(?P<activation_key>[\w.@+-:]+)/$',
        ActivationView.as_view(),
        name='registration_activate'),
    url(r'^register/$',
        RegistrationView.as_view(),
        name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'
        ),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'
        ),
        name='registration_disallowed'),
    url(r'', include('registration.auth_urls')),
]
