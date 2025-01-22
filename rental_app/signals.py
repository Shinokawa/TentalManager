from django.db.models.signals import post_save, post_delete, pre_delete, m2m_changed
from django.dispatch import receiver
from .models import Contract, Fee, Payment, Property
from django.db.models import Sum

@receiver(post_save, sender=Contract)
def create_fees(sender, instance, created, **kwargs):
    if created:
        # 生成租金费用（假设每月一次）
        Fee.objects.create(
            contract=instance,
            category='rent',
            amount=instance.monthly_rent,
            term='每月',
            is_collected=False
        )
        '''
        # 生成保证金（一次性）
        Fee.objects.create(
            contract=instance,
            category='deposit',
            amount=instance.monthly_rent * 2,  # 假设保证金为2个月租金
            term='一次性',
            is_collected=False
        )
        
        # 生成物业管理费（假设每月一次）
        Fee.objects.create(
            contract=instance,
            category='management_fee',
            amount=100,  # 示例金额
            term='每月',
            is_collected=False
        )
        '''
        # 根据需求生成其他费用

@receiver(post_save, sender=Payment)
def update_fee_status(sender, instance, created, **kwargs):
    if created:
        fee = instance.fee
        
        # 检查该费用的所有支付总额是否达到或超过费用金额
        total_paid = Payment.objects.filter(fee=fee).aggregate(total=Sum('amount'))['total'] or 0
        
        if total_paid >= fee.amount:
            fee.is_collected = True
            fee.payment_method = instance.payment_method
            fee.receipt = instance.receipt
            fee.save()

@receiver(post_delete, sender=Payment)
def revert_fee_status(sender, instance, **kwargs):
    fee = instance.fee
    # 重新计算总支付金额
    total_paid = Payment.objects.filter(fee=fee).exclude(id=instance.id).aggregate(total=Sum('amount'))['total'] or 0
    
    if total_paid < fee.amount:
        fee.is_collected = False
        fee.save()

@receiver(pre_delete, sender=Contract)
def update_property_status(sender, instance, **kwargs):
    # 合同删除时更新房产状态
    for property in instance.properties.all():
        property.update_rental_status('available')

@receiver(m2m_changed, sender=Contract.properties.through)
def handle_property_changes(sender, instance, action, reverse, model, pk_set, **kwargs):
    """处理合同和房源多对多关系变化"""
    if action == "post_remove":
        # 当房源从合同中移除时，将状态改为可用
        Property.objects.filter(id__in=pk_set).update(rental_status='available')
    elif action == "post_add":
        # 当新房源添加到合同时，将状态改为已租赁
        Property.objects.filter(id__in=pk_set).update(rental_status='rented')