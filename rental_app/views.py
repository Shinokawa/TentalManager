# rental_app/views.py

from rest_framework import viewsets, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Sum
from .models import Tenant, Property, Contract, Fee, Payment
from .serializers import (
    TenantSerializer, PropertySerializer,
    ContractSerializer, FeeSerializer, PaymentSerializer
)

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all().select_related('tenant').prefetch_related('properties')
    serializer_class = ContractSerializer
    permission_classes = [permissions.IsAuthenticated]

class FeeViewSet(viewsets.ModelViewSet):
    queryset = Fee.objects.all().select_related('contract')
    serializer_class = FeeSerializer
    permission_classes = [permissions.IsAuthenticated]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('fee__contract')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def receivables(self, request):
        receivables = Fee.objects.filter(is_collected=False)
        serializer = FeeSerializer(receivables, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def payables(self, request):
        payables = Fee.objects.filter(overdue_status='overdue', is_collected=False)
        serializer = FeeSerializer(payables, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        payment = serializer.save()
        fee = payment.fee
        fee.is_collected = True
        fee.payment_method = payment.payment_method
        fee.receipt = payment.receipt
        fee.save()

@api_view(['GET'])
def data_analysis(request):
    receivable_amount = Fee.objects.filter(is_collected=False).aggregate(total=Sum('amount'))['total'] or 0
    received_amount = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    overdue_amount = Fee.objects.filter(overdue_status='overdue', is_collected=False).aggregate(total=Sum('amount'))['total'] or 0
    collection_rate = (received_amount / receivable_amount) * 100 if receivable_amount else 0

    total_area = Property.objects.aggregate(total=Sum('area'))['total'] or 0
    rented_area = Property.objects.filter(rental_status='rented').aggregate(total=Sum('area'))['total'] or 0
    available_properties = Property.objects.filter(rental_status='available').count()
    rental_rate = (rented_area / total_area) * 100 if total_area else 0

    data = {
        'financial': {
            'receivable_amount': receivable_amount,
            'received_amount': received_amount,
            'overdue_amount': overdue_amount,
            'collection_rate': collection_rate,
        },
        'property': {
            'total_area': total_area,
            'rented_area': rented_area,
            'available_properties': available_properties,
            'rental_rate': rental_rate,
        }
    }
    return Response(data)