from django.urls import path
from .views import DeliveryOrderPriceView



urlpatterns = [
    path('api/v1/delivery-order-price', DeliveryOrderPriceView.as_view(), name='delivery-order-price'),
]