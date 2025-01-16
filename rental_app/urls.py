from django.urls import include, path
from rest_framework import routers
from .views import TenantViewSet, PropertyViewSet, ContractViewSet, FeeViewSet, PaymentViewSet, data_analysis

router = routers.DefaultRouter()
router.register(r'tenants', TenantViewSet)
router.register(r'properties', PropertyViewSet)
router.register(r'contracts', ContractViewSet)
router.register(r'fees', FeeViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('data-analysis/', data_analysis, name='data-analysis'),
]