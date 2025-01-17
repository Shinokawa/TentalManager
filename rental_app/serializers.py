# rental_app/serializers.py

from rest_framework import serializers
from .models import Tenant, Property, Contract, Fee, Payment

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'

class ContractSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    tenant_id = serializers.PrimaryKeyRelatedField(
        queryset=Tenant.objects.all(), source='tenant', write_only=True
    )
    properties = PropertySerializer(many=True, read_only=True)
    property_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Property.objects.all(), write_only=True, source='properties'
    )

    class Meta:
        model = Contract
        fields = [
            'id', 'tenant', 'tenant_id', 'properties', 'property_ids',
            'start_date', 'end_date', 'monthly_rent', 'yearly_rent',
            'total_rent', 'rental_area', 'rental_unit_price', 'rent_collection_time',
            'status', 'current_receivable', 'current_outstanding', 'total_overdue',
        ]

    def create(self, validated_data):
        tenant = validated_data.pop('tenant')
        properties = validated_data.pop('properties')
        contract = Contract.objects.create(tenant=tenant, **validated_data)
        contract.properties.set(properties)
        return contract

    def update(self, instance, validated_data):
        tenant = validated_data.pop('tenant', None)
        properties = validated_data.pop('properties', None)

        if tenant is not None:
            instance.tenant = tenant

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if properties is not None:
            instance.properties.set(properties)

        return instance

class FeeSerializer(serializers.ModelSerializer):
    contract = ContractSerializer(read_only=True)
    contract_id = serializers.PrimaryKeyRelatedField(
        queryset=Contract.objects.all(), source='contract', write_only=True
    )

    class Meta:
        model = Fee
        fields = [
            'id', 'contract', 'contract_id',
            'category', 'amount', 'term',
            'is_collected', 'overdue_status', 'payment_method', 'receipt', 'bank_slip',
        ]

class PaymentSerializer(serializers.ModelSerializer):
    fee = FeeSerializer(read_only=True)
    fee_id = serializers.PrimaryKeyRelatedField(
        queryset=Fee.objects.all(), source='fee', write_only=True
    )

    class Meta:
        model = Payment
        fields = ['id', 'fee', 'fee_id', 'payment_date', 'amount', 'payment_method', 'receipt']