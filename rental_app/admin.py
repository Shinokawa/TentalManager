# rental_app/admin.py

from django.contrib import admin
from .models import Tenant, Property, Contract, Fee, Payment

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone_number')
    search_fields = ('first_name', 'last_name', 'email', 'phone_number')
    ordering = ('email',)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('house_number', 'address', 'area', 'rental_status', 'current_value')
    search_fields = ('house_number', 'address')

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'start_date', 'end_date', 'status')
    search_fields = ('id', 'tenant__email')
    filter_horizontal = ('properties',)  # 添加此行以支持多选界面

@admin.register(Fee)
class FeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'contract', 'category', 'amount', 'term', 'is_collected', 'overdue_status')
    search_fields = ('contract__id', 'category', 'term')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'fee', 'payment_date', 'amount', 'payment_method')
    search_fields = ('fee__id', 'payment_method')