from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Contract, Fee

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