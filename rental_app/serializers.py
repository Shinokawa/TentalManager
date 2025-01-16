from rest_framework import serializers
from .models import Tenant, Property, Contract, Fee, Payment

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number']

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = '__all__'

class ContractSerializer(serializers.ModelSerializer):
    customer = TenantSerializer(read_only=True)
    property = PropertySerializer(read_only=True)

    class Meta:
        model = Contract
        fields = '__all__'

class FeeSerializer(serializers.ModelSerializer):
    contract = ContractSerializer(read_only=True)

    class Meta:
        model = Fee
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    fee = FeeSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = '__all__'