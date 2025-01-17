from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Contract, Fee, Payment
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