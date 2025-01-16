
目录
	1.	项目概述
	2.	技术栈
	3.	数据模型
	4.	API 端点
	5.	认证与权限
	6.	Celery 任务
	7.	邮件模板
	8.	开发环境设置
	9.	部署说明
	10.	常见问题与解决方案
	11.	附录

1. 项目概述

租赁管理系统 是一个用于管理房产租赁、合同、费用和支付的后端系统。系统支持租户信息管理、房产信息管理、租赁合同管理、费用生成与收取、支付记录管理，并通过 Celery 定时任务自动发送缴费通知和逾期通知邮件。

主要功能包括：
	•	租户管理：记录租户的基本信息，如姓名、邮箱、电话等。
	•	房产管理：管理房产信息，包括房号、地址、面积、当前状态等。
	•	合同管理：记录租赁合同，关联租户和房产，包含租金、租期等信息。
	•	费用管理：生成租金、保证金、物业管理费等费用记录，跟踪缴纳状态。
	•	支付管理：记录租户的支付记录，支持多种支付方式。
	•	数据分析：提供财务和房产的关键指标分析。
	•	通知系统：通过 Celery 定时任务自动发送缴费通知和逾期通知邮件。

2. 技术栈
	•	后端框架：Django 4.2
	•	API 框架：Django REST Framework (DRF) 3.14.0
	•	任务队列：Celery 5.3.0
	•	定时任务调度：django-celery-beat 2.5.0
	•	数据库：PostgreSQL
	•	消息中间件：Redis 4.5.4
	•	邮件服务：SMTP 服务器（如 Gmail, SendGrid 等）
	•	开发环境管理：Anaconda 环境
	•	版本控制：Git
	•	前端框架：待定（假设为 React/Vue 等）

3. 数据模型

项目中的主要数据模型及其关系如下：

3.1 Tenant（租户）

class Tenant(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    # 其他字段，如地址等

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

	•	描述：记录租户的基本信息。
	•	字段：
	•	email：租户的电子邮件地址，唯一。
	•	first_name：租户的名。
	•	last_name：租户的姓。
	•	phone_number：租户的电话号码。

3.2 Property（房产）

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

	•	描述：管理房产信息。
	•	字段：
	•	house_number：房号，唯一。
	•	area：房产面积（平方米）。
	•	address：房产地址。
	•	rental_status：租赁状态（已租赁、未租赁、维护中）。
	•	current_value：当前价值。
	•	maintenance_status：维护状态描述。

3.3 Contract（合同）

class Contract(models.Model):
    STATUS_CHOICES = [
        ('active', '有效'),
        ('terminated', '终止'),
        ('expired', '过期'),
    ]

    tenant = models.ForeignKey(Tenant, related_name='contracts', on_delete=models.CASCADE)
    property = models.ForeignKey(Property, related_name='contracts', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    yearly_rent = models.DecimalField(max_digits=10, decimal_places=2)
    total_rent = models.DecimalField(max_digits=12, decimal_places=2)
    rental_area = models.DecimalField(max_digits=10, decimal_places=2)
    rental_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    rent_collection_time = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_receivable = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    current_outstanding = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_overdue = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Contract {self.id} - {self.property.house_number} - {self.tenant.email}"

	•	描述：记录租赁合同，关联租户和房产。
	•	字段：
	•	tenant：外键，关联 Tenant 模型。
	•	property：外键，关联 Property 模型。
	•	start_date：合同开始日期。
	•	end_date：合同结束日期。
	•	monthly_rent：月租金。
	•	yearly_rent：年租金。
	•	total_rent：总租金。
	•	rental_area：租赁面积。
	•	rental_unit_price：租赁单价。
	•	rent_collection_time：租金收取时间。
	•	status：合同状态（有效、终止、过期）。
	•	current_receivable：当前应收金额。
	•	current_outstanding：当前未结金额。
	•	total_overdue：累计逾期金额。

3.4 Fee（费用）

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

	•	描述：记录租赁合同中的各类费用。
	•	字段：
	•	contract：外键，关联 Contract 模型。
	•	category：费用类别（保证金、租金、物业管理费等）。
	•	amount：费用金额。
	•	term：费用所属期（如 ‘2025-01’）。
	•	is_collected：是否已收取。
	•	overdue_status：是否逾期（按时、逾期）。
	•	payment_method：支付方式（POS、微信、支付宝、银行转账、其他）。
	•	receipt：收据上传。
	•	bank_slip：银行凭证上传。

3.5 Payment（支付记录）

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

	•	描述：记录租户的支付记录。
	•	字段：
	•	fee：外键，关联 Fee 模型。
	•	payment_date：支付日期。
	•	amount：支付金额。
	•	payment_method：支付方式（POS、微信、支付宝、银行转账、其他）。
	•	receipt：支付收据上传。

4. API 端点

使用 Django REST Framework (DRF) 提供了 RESTful API 接口，供前端进行数据交互。以下是主要的 API 端点及其说明。

4.1 认证相关
	•	登录：/api-auth/login/
	•	登出：/api-auth/logout/

说明：使用 DRF 提供的浏览器登录界面进行认证。建议在前端使用 Token 或 JWT 进行认证，以实现无状态的 API 调用。

4.2 租户（Tenant）
	•	列表与创建：GET /api/tenants/、POST /api/tenants/
	•	详情、更新与删除：GET /api/tenants/{id}/、PUT /api/tenants/{id}/、PATCH /api/tenants/{id}/、DELETE /api/tenants/{id}/

字段：
	•	id：租户ID
	•	first_name：名
	•	last_name：姓
	•	email：邮箱
	•	phone_number：电话号码

4.3 房产（Property）
	•	列表与创建：GET /api/properties/、POST /api/properties/
	•	详情、更新与删除：GET /api/properties/{id}/、PUT /api/properties/{id}/、PATCH /api/properties/{id}/、DELETE /api/properties/{id}/

字段：
	•	id：房产ID
	•	house_number：房号
	•	area：面积
	•	address：地址
	•	rental_status：租赁状态
	•	current_value：当前价值
	•	maintenance_status：维护状态

4.4 合同（Contract）
	•	列表与创建：GET /api/contracts/、POST /api/contracts/
	•	详情、更新与删除：GET /api/contracts/{id}/、PUT /api/contracts/{id}/、PATCH /api/contracts/{id}/、DELETE /api/contracts/{id}/

字段：
	•	id：合同ID
	•	tenant：关联的租户（租户ID）
	•	property：关联的房产（房产ID）
	•	start_date：开始日期
	•	end_date：结束日期
	•	monthly_rent：月租金
	•	yearly_rent：年租金
	•	total_rent：总租金
	•	rental_area：租赁面积
	•	rental_unit_price：租赁单价
	•	rent_collection_time：租金收取时间
	•	status：合同状态
	•	current_receivable：当前应收金额
	•	current_outstanding：当前未结金额
	•	total_overdue：累计逾期金额

4.5 费用（Fee）
	•	列表与创建：GET /api/fees/、POST /api/fees/
	•	详情、更新与删除：GET /api/fees/{id}/、PUT /api/fees/{id}/、PATCH /api/fees/{id}/、DELETE /api/fees/{id}/

字段：
	•	id：费用ID
	•	contract：关联的合同（合同ID）
	•	category：费用类别
	•	amount：费用金额
	•	term：费用所属期
	•	is_collected：是否已收取
	•	overdue_status：是否逾期
	•	payment_method：支付方式
	•	receipt：收据文件
	•	bank_slip：银行凭证文件

4.6 支付记录（Payment）
	•	列表与创建：GET /api/payments/、POST /api/payments/
	•	详情、更新与删除：GET /api/payments/{id}/、PUT /api/payments/{id}/、PATCH /api/payments/{id}/、DELETE /api/payments/{id}/

字段：
	•	id：支付ID
	•	fee：关联的费用（费用ID）
	•	payment_date：支付日期
	•	amount：支付金额
	•	payment_method：支付方式
	•	receipt：支付收据文件

4.7 数据分析（Data Analysis）
	•	端点：GET /api/data-analysis/

功能：提供财务和房产的关键指标数据。

响应示例：

{
    "financial": {
        "receivable_amount": 50000.00,
        "received_amount": 45000.00,
        "overdue_amount": 5000.00,
        "collection_rate": 90.0
    },
    "property": {
        "total_area": 1000.00,
        "rented_area": 800.00,
        "available_properties": 5,
        "rental_rate": 80.0
    }
}

5. 认证与权限

项目使用 Django REST Framework (DRF) 提供的认证机制。默认情况下，所有 API 端点都需要经过认证才能访问。

5.1 认证方式
	•	Token-Based Authentication：建议使用 DRF 的 Token Authentication 或 JWT（JSON Web Token）进行认证，以便前端通过令牌与后端进行通信。

5.2 权限设置
	•	IsAuthenticated：仅允许已认证用户访问 API 端点。
	•	自定义权限（可选）：根据角色（如管理员、普通用户等）设置不同的访问权限。

示例权限配置：

# rental_management/settings.py

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',  # 或 'rest_framework_simplejwt.authentication.JWTAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

6. Celery 任务

项目使用 Celery 处理异步任务，主要用于定时发送缴费通知和逾期通知邮件。

6.1 配置

# rental_management/settings.py

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'send-payment-notifications-monthly': {
        'task': 'rental_app.tasks.send_payment_notifications',
        'schedule': crontab(day_of_month=1, hour=9, minute=0),  # 每月1日9:00发送缴费通知
    },
    'send-overdue-notifications-daily': {
        'task': 'rental_app.tasks.send_overdue_notifications',
        'schedule': crontab(hour=10, minute=0),  # 每天10:00发送逾期通知
    },
}

6.2 任务定义

# rental_app/tasks.py

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import date
from .models import Fee

@shared_task
def send_payment_notifications():
    today = date.today()
    # 每月的第一天发送通知
    if today.day != 1:
        return
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

6.3 启动 Celery

需要同时启动 Celery Worker 和 Celery Beat：
	•	终端 1：启动 Celery Worker

celery -A rental_management worker -l info


	•	终端 2：启动 Celery Beat

celery -A rental_management beat -l info

7. 邮件模板

项目使用 Django 的模板系统来生成邮件内容，位于 templates/emails/ 目录下。

7.1 缴费通知模板

<!-- templates/emails/payment_notification.html -->

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>缴费通知</title>
</head>
<body>
    <p>尊敬的{{ tenant.first_name }} {{ tenant.last_name }}，</p>
    <p>您好！这是您的缴费通知：</p>
    <ul>
        <li>费用类别：{{ fee.get_category_display }}</li>
        <li>金额：{{ fee.amount }}</li>
        <li>缴费截止日期：{{ fee.term }}</li>
    </ul>
    <p>请您在规定时间内完成缴费，谢谢合作！</p>
    <p>此致，</p>
    <p>租赁管理团队</p>
</body>
</html>

7.2 逾期缴费通知模板

<!-- templates/emails/overdue_notification.html -->

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>逾期缴费通知</title>
</head>
<body>
    <p>尊敬的{{ tenant.first_name }} {{ tenant.last_name }}，</p>
    <p>您好！您的以下费用已经逾期未缴：</p>
    <ul>
        <li>费用类别：{{ fee.get_category_display }}</li>
        <li>金额：{{ fee.amount }}</li>
        <li>原定缴费日期：{{ fee.term }}</li>
    </ul>
    <p>请您尽快完成缴费，以免影响您的租赁状态。</p>
    <p>此致，</p>
    <p>租赁管理团队</p>
</body>
</html>

8. 开发环境设置

以下是项目的开发环境设置指南，确保前端开发人员能够顺利与后端进行集成。

8.1 环境要求
	•	Python：3.12
	•	虚拟环境管理：Anaconda
	•	数据库：PostgreSQL
	•	消息中间件：Redis
	•	依赖管理：requirements.txt

8.2 环境配置步骤
	1.	克隆项目仓库

git clone https://github.com/your-repo/rental_management.git
cd rental_management


	2.	创建并激活 Anaconda 虚拟环境

conda create -n managest python=3.12
conda activate managest


	3.	安装依赖
确保 requirements.txt 包含以下内容：

Django==4.2
djangorestframework==3.14.0
psycopg2-binary==2.9.6
celery>=5.3.0
redis==4.5.4
django-celery-beat>=2.5.0
gunicorn==20.1.0
django-cors-headers==3.14.0  # 如需跨域支持

运行安装命令：

pip install --upgrade pip
pip install -r requirements.txt


	4.	配置数据库
确保 PostgreSQL 已安装并运行，创建数据库和用户：

CREATE DATABASE rental_db;
CREATE USER rental_user WITH PASSWORD 'rental_password';
GRANT ALL PRIVILEGES ON DATABASE rental_db TO rental_user;


	5.	配置 Redis
确保 Redis 已安装并运行：

brew install redis  # macOS 使用 Homebrew 安装
brew services start redis
redis-cli ping
# 预期输出: PONG


	6.	配置环境变量
在 rental_management/settings.py 中，设置数据库、Celery、邮件等相关配置：

# rental_management/settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'rental_db',
        'USER': 'rental_user',
        'PASSWORD': 'rental_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_BEAT_SCHEDULE = {
    'send-payment-notifications-monthly': {
        'task': 'rental_app.tasks.send_payment_notifications',
        'schedule': crontab(day_of_month=1, hour=9, minute=0),
    },
    'send-overdue-notifications-daily': {
        'task': 'rental_app.tasks.send_overdue_notifications',
        'schedule': crontab(hour=10, minute=0),
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.your_email_provider.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your_email@example.com'
EMAIL_HOST_PASSWORD = 'your_email_password'
DEFAULT_FROM_EMAIL = 'your_email@example.com'

# CORS 配置（如需）
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://your-frontend-domain.com",
]


	7.	运行数据库迁移

python manage.py makemigrations rental_app
python manage.py migrate


	8.	创建超级用户

python manage.py createsuperuser


	9.	启动 Celery Worker 和 Celery Beat
	•	终端 1：

celery -A rental_management worker -l info


	•	终端 2：

celery -A rental_management beat -l info


	10.	启动 Django 开发服务器

python manage.py runserver


	11.	访问管理后台
打开浏览器，访问 http://localhost:8000/admin/，使用超级用户账号登录。

9. 部署说明

（视项目需求，提供生产环境的部署指南，如使用 Docker、Gunicorn、Nginx 等）

10. 常见问题与解决方案

10.1 迁移错误
	•	错误：

django.core.exceptions.ImproperlyConfigured: AUTH_USER_MODEL refers to model 'rental_app.Customer' that has not been installed


	•	解决方法：
	1.	确认 settings.py 中的 AUTH_USER_MODEL 设置正确。如果不使用自定义用户模型，移除或注释掉该设置。
	2.	确保 models.py 中没有错误的用户模型定义。
	3.	清理并重新生成迁移文件，重置数据库（仅适用于开发阶段）。

10.2 Celery 无法启动
	•	错误：

AttributeError: 'EntryPoints' object has no attribute 'get'


	•	解决方法：
	•	确保安装了兼容 Python 3.12 的 Celery 版本（>=5.3.0）。
	•	更新依赖并重新安装。

10.3 邮件发送失败
	•	错误：
	•	无法连接到 SMTP 服务器
	•	邮件被标记为垃圾邮件
	•	解决方法：
	1.	确认 EMAIL_BACKEND 和相关邮件配置正确。
	2.	检查 SMTP 服务器的可用性和凭证。
	3.	使用可信的发件邮箱，避免被标记为垃圾邮件。

11. 附录

11.1 模型关系图

Tenant <--1:M--> Contract <--1:M--> Fee <--1:M--> Payment
Property <--1:M--> Contract

11.2 API 文档示例

（可使用工具如 Swagger 或 DRF 的自动生成文档）

11.3 参考资源
	•	Django 官方文档
	•	Django REST Framework 官方文档
	•	Celery 官方文档
	•	django-celery-beat 官方文档
	•	PostgreSQL 官方文档
	•	Redis 官方文档

结语

通过以上详细的项目文档，前端开发团队应能够充分理解后端系统的结构、API 端点及其数据交互方式，从而高效地进行前端开发与集成。如果在开发过程中遇到任何问题或需要进一步的支持，请随时与后端开发团队沟通。

祝您的前端开发顺利！

附注：根据项目实际情况，您可以进一步补充或调整文档内容，例如详细的 API 请求与响应示例、认证流程、错误处理机制等，以满足前端开发的具体需求。