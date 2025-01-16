from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import date
from .models import Fee

@shared_task
def send_payment_notifications():
    today = date.today()
    # 假设每月的第一天发送通知
    fees_due = Fee.objects.filter(
        term__startswith=f"{today.year}-{today.month:02}",
        is_collected=False,
        overdue_status='on_time'
    )
    for fee in fees_due:
        tenant = fee.contract.tenant
        subject = "缴费通知"
        message = render_to_string('emails/payment_notification.html', {
            'tenant': tenant,
            'fee': fee,
        })
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [tenant.email])

@shared_task
def send_overdue_notifications():
    overdue_fees = Fee.objects.filter(overdue_status='overdue', is_collected=False)
    for fee in overdue_fees:
        tenant = fee.contract.tenant
        subject = "逾期缴费通知"
        message = render_to_string('emails/overdue_notification.html', {
            'tenant': tenant,
            'fee': fee,
        })
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [tenant.email])