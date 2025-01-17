from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from decimal import Decimal

class Tenant(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    # 添加其他字段，如地址等

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class Property(models.Model):
    RENTAL_STATUS_CHOICES = [
        ('rented', '已租赁'),
        ('available', '未租赁'),
        ('maintenance', '维护中'),
    ]

    house_number = models.CharField(max_length=20, unique=True)
    area = models.DecimalField(max_digits=10, decimal_places=2)  # 平方米
    address = models.CharField(max_length=255)
    rental_status = models.CharField(max_length=20, choices=RENTAL_STATUS_CHOICES, default='available')
    current_value = models.DecimalField(max_digits=12, decimal_places=2)
    maintenance_status = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.house_number} - {self.address}"

    def update_rental_status(self, new_status):
        self.rental_status = new_status
        self.save()

class Contract(models.Model):
    STATUS_CHOICES = [
        ('active', '有效'),
        ('terminated', '终止'),
        ('expired', '过期'),
    ]

    tenant = models.ForeignKey(Tenant, related_name='contracts', on_delete=models.CASCADE)
    properties = models.ManyToManyField(Property, related_name='contracts')
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    yearly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    total_rent = models.DecimalField(max_digits=12, decimal_places=2)
    rental_area = models.DecimalField(max_digits=10, decimal_places=2)
    rental_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    rent_collection_time = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_receivable = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    current_outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    total_overdue = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True, verbose_name='合同文件')
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], verbose_name='保证金')
    management_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))], verbose_name='物业管理费')
    business_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='经营业态')
    rental_purpose = models.TextField(blank=True, null=True, verbose_name='租赁用途')
    decoration_period = models.IntegerField(default=0, verbose_name='装修期(天)')
    rent_free_period = models.IntegerField(default=0, verbose_name='免租期(天)')
    utilities_payment = models.TextField(blank=True, null=True, verbose_name='水电费支付方式')
    promotion_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='推广费')

    def __str__(self):
        return f"Contract {self.id} - Tenant: {self.tenant.email}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # 更新所有相关房产状态
            for property in self.properties.all():
                property.update_rental_status('rented')
            
            # 创建初始费用
            self.create_initial_fees()

    def create_initial_fees(self):
        from .models import Fee
        # 创建保证金费用
        Fee.objects.create(
            contract=self,
            category='deposit',
            amount=self.deposit_amount,
            term='一次性',
            is_collected=False
        )
        # 创建首月物业管理费
        Fee.objects.create(
            contract=self,
            category='management_fee',
            amount=self.management_fee,
            term=self.start_date.strftime('%Y-%m'),
            is_collected=False
        )

class Fee(models.Model):
    CATEGORY_CHOICES = [
        ('deposit', '保证金'),
        ('rent', '租金'),
        ('management_fee', '物业管理费'),
        # 可以添加其他费用类别
    ]

    OVERDUE_STATUS_CHOICES = [
        ('on_time', '按时'),
        ('overdue', '逾期'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('POS', 'POS'),
        ('wechat', '微信'),
        ('alipay', '支付宝'),
        ('bank_transfer', '银行转账'),
        ('other', '其他'),
    ]

    contract = models.ForeignKey(Contract, related_name='fees', on_delete=models.CASCADE)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    term = models.CharField(max_length=50)  # 例如 '2025-01'
    is_collected = models.BooleanField(default=False)
    overdue_status = models.CharField(max_length=20, choices=OVERDUE_STATUS_CHOICES, default='on_time')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    bank_slip = models.FileField(upload_to='bank_slips/', blank=True, null=True)

    def __str__(self):
        return f"{self.category} - {self.amount} - {self.contract}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # 更新合同状态
        self.update_contract_status()

    def update_contract_status(self):
        contract = self.contract
        # 更新合同相关金额
        contract.current_receivable = contract.fees.filter(is_collected=False).aggregate(total=Sum('amount'))['total'] or 0
        contract.current_outstanding = contract.fees.filter(is_collected=False, overdue_status='overdue').aggregate(total=Sum('amount'))['total'] or 0
        contract.total_overdue = contract.fees.filter(overdue_status='overdue').aggregate(total=Sum('amount'))['total'] or 0
        contract.save()

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('POS', 'POS'),
        ('wechat', '微信'),
        ('alipay', '支付宝'),
        ('bank_transfer', '银行转账'),
        ('other', '其他'),
    ]

    fee = models.ForeignKey(Fee, related_name='payments', on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    receipt = models.FileField(upload_to='payment_receipts/', blank=True, null=True)

    def __str__(self):
        return f"Payment {self.id} - {self.amount}"
    
    def generate_receipt(self):
        from django.template.loader import render_to_string
        from weasyprint import HTML
        import tempfile
        
        # 生成收据HTML
        context = {
            'payment': self,
            'contract': self.fee.contract,
            'tenant': self.fee.contract.tenant
        }
        html_string = render_to_string('receipts/payment_receipt.html', context)
        
        # 转换为PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
            HTML(string=html_string).write_pdf(pdf_file.name)
            return pdf_file.name