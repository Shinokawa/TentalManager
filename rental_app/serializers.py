# rental_app/serializers.py

from rest_framework import serializers
from rest_framework.reverse import reverse
from .models import Tenant, Property, Contract, Fee, Payment
from django.db import models

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
        
        # 更新房源状态
        for property in properties:
            property.rental_status = 'rented'
            property.save()
        
        return contract

    def update(self, instance, validated_data):
        tenant = validated_data.pop('tenant', None)
        properties = validated_data.pop('properties', None)

        if tenant is not None:
            instance.tenant = tenant

        # 如果更新了房源，需要处理旧房源和新房源的状态
        if properties is not None:
            # 将原有房源状态改为可用
            for property in instance.properties.all():
                property.rental_status = 'available'
                property.save()
            
            # 设置新的房源关系
            instance.properties.set(properties)
            
            # 将新房源状态改为已租赁
            for property in properties:
                property.rental_status = 'rented'
                property.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

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
    receipt_url = serializers.SerializerMethodField()
    print_receipt_url = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ['id', 'fee', 'fee_id', 'payment_date', 'amount', 
                 'payment_method', 'receipt', 'receipt_url', 'print_receipt_url']

    def validate(self, data):
        """验证支付金额"""
        fee = data.get('fee')
        amount = data.get('amount')
        
        if fee and amount:
            if amount <= 0:
                raise serializers.ValidationError({"amount": "支付金额必须大于0"})
            # 检查剩余应付金额
            total_paid = Payment.objects.filter(fee=fee).aggregate(
                total=models.Sum('amount'))['total'] or 0
            remaining = fee.amount - total_paid
            if amount > remaining:
                raise serializers.ValidationError(
                    {"amount": f"支付金额不能超过剩余应付金额 {remaining}"}
                )
        return data

    def get_receipt_url(self, obj):
        if obj.receipt:
            return obj.receipt.url
        return None

    def get_print_receipt_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return None
        return reverse('payment-print-receipt', args=[obj.pk], request=request)