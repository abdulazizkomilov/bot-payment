from django.urls import path
from .views import TestView, PaycomInitializationView

urlpatterns = [
    path("paycom/init/", PaycomInitializationView.as_view(), name="paycom-init"),
    path('paycom/', TestView.as_view(), name='paycom'),
]
