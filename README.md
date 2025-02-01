# 租赁管理系统项目文档

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [数据模型](#3-数据模型)
4. [API 端点](#4-api-端点)
5. [认证与权限](#5-认证与权限)
6. [Celery 任务](#6-celery-任务)
7. [邮件模板](#7-邮件模板)
8. [开发环境设置](#8-开发环境设置)
9. [部署说明](#9-部署说明)
10. [常见问题与解决方案](#10-常见问题与解决方案)
11. [附录](#11-附录)

---

## 1. 项目概述

**租赁管理系统** 是一个用于管理房产租赁、合同、费用和支付的后端系统。系统支持租户信息管理、房产信息管理、租赁合同管理、费用生成与收取、支付记录管理，并通过 Celery 定时任务自动发送缴费通知和逾期通知邮件。

**主要功能包括：**

- **租户管理**：记录租户的基本信息，如姓名、邮箱、电话等。
- **房产管理**：管理房产信息，包括房号、地址、面积、当前状态等。
- **合同管理**：记录租赁合同，关联租户和房产，包含租金、租期等信息。
- **费用管理**：生成租金、保证金、物业管理费等费用记录，跟踪缴纳状态。
- **支付管理**：记录租户的支付记录，支持多种支付方式。
- **数据分析**：提供财务和房产的关键指标分析。
- **通知系统**：通过 Celery 定时任务自动发送缴费通知和逾期通知邮件。

---

## 2. 技术栈

- **后端框架**：Django 4.2
- **API 框架**：Django REST Framework (DRF) 3.14.0
- **任务队列**：Celery 5.3.0
- **定时任务调度**：django-celery-beat 2.5.0
- **数据库**：PostgreSQL
- **消息中间件**：Redis 4.5.4
- **邮件服务**：SMTP 服务器（如 Gmail, SendGrid 等）
- **开发环境管理**：Anaconda 环境
- **版本控制**：Git
- **前端框架**：待定（假设为 React/Vue 等）

---

## 3. 数据模型

项目中的主要数据模型及其关系如下：

### 3.1 Tenant（租户）

```python
class Tenant(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    # 其他字段，如地址等

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
```
- 描述：记录租户的基本信息。
  
- 字段：
  
  - email: 租户的电子邮件地址，唯一。
  - first_name: 租户的名字。
  - last_name: 租户的姓。
  - phone_number: 租户的电话号码。

### 3.2 Property（房产）
```python
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
```
- 描述：管理房产信息。

- 字段：

  - house_number：房号，唯一。
  - area：房产面积（平方米）。
  - address：房产地址。
  - rental_status：租赁状态（已租赁、未租赁、维护中）。
  - current_value：当前价值。
  - maintenance_status：维护状态描述。

### 3.3 Contract（合同）
```python
class Contract(models.Model):
    STATUS_CHOICES = [
        ('active', '有效'),
        ('terminated', '终止'),
        ('expired', '过期'),
    ]

    tenant = models.ForeignKey(Tenant, related_name='contracts', on_delete=models.CASCADE)
    properties = models.ManyToManyField(Property, related_name='contracts', on_delete=models.CASCADE)
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
```
- 描述：记录租赁合同，关联租户和房产。

- 字段：

  - tenant：外键，关联 Tenant 模型。
  - properties：多对多关系，关联 Property 模型。
  - start_date：合同开始日期。
  - end_date：合同结束日期。
  - monthly_rent：月租金。
  - yearly_rent：年租金。
  - total_rent：总租金。
  - rental_area：租赁面积。
  - rental_unit_price：租赁单价。
  - rent_collection_time：租金收取时间。
  - status：合同状态（有效、终止、过期）。
  - current_receivable：当前应收金额。
  - current_outstanding：当前未结金额。
  - total_overdue：累计逾期金额。
  - contract_file：合同文件。
  - deposit_amount：保证金金额。
  - management_fee：物业管理费。
  - business_type：经营业态。
  - rental_purpose：租赁用途。
  - decoration_period：装修期（天）。
  - rent_free_period：免租期（天）。
  - utilities_payment：水电费支付方式。
  - promotion_fee：推广费。

创建合同示例：
```
POST /api/contracts/
{
    "tenant_id": 1,
    "property_ids": [1, 2, 3],
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "monthly_rent": "2000.00",
    "yearly_rent": "24000.00",
    "total_rent": "24000.00",
    "rental_area": "120.50",
    "rental_unit_price": "2000.00",
    "rent_collection_time": "2025-01-01",
    "status": "active",
    "current_receivable": "2000.00",
    "current_outstanding": "0.00",
    "total_overdue": "0.00"
}
```
### 3.4 Fee（费用）
```python
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
    payment_method = models.CharField(maxlength=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    bank_slip = models.FileField(upload_to='bank_slips/', blank=True, null=True)

    def __str__(self):
        return f"{self.category} - {self.amount} - {self.contract}"
```
- 描述：记录租赁合同中的各类费用。

- 字段：
  - contract：外键，关联 Contract 模型。
  - category：费用类别（保证金、租金、物业管理费等）。
  - amount：费用金额。
  - term：费用所属期（如 ‘2025-01’）。
  - is_collected：是否已收取。
  - overdue_status：是否逾期（按时、逾期）。
  - payment_method：支付方式（POS、微信、支付宝、银行转账、其他）。
  - receipt：收据上传。
  - bank_slip：银行凭证上传。

### 3.5 Payment（支付记录）
```python
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
```
- 描述：记录租户的支付记录。

- 字段：
  - fee：外键，关联 Fee 模型。
  - payment_date：支付日期。
  - amount：支付金额。
  - payment_method：支付方式（POS、微信、支付宝、银行转账、其他）。
  - receipt：支付收据上传。

## 4. API 端点

使用 Django REST Framework (DRF) 提供了 RESTful API 接口，供前端进行数据交互。以下是主要的 API 端点及其说明。

### 4.1 认证相关
- 登录：/api-auth/login/
- 登出：/api-auth/logout/

说明：使用 DRF 提供的浏览器登录界面进行认证。建议在前端使用 Token 或 JWT 进行认证，以实现无状态的 API 调用。

### 4.2 租户（Tenant）
- 列表与创建：GET /api/tenants/、POST /api/tenants/
- 详情、更新与删除：GET /api/tenants/{id}/、PUT /api/tenants/{id}/、PATCH /api/tenants/{id}/、DELETE /api/tenants/{id}/
- 获取客户费用清单: GET /api/tenants/{d}/fees/
- 发送费用通知: POST /api/tenants/{tenant_id}/send_notification/

字段：
- id：租户ID
- first_name：名
- last_name：姓
- email：邮箱
- phone_number：电话号码

### 4.3 房产（Property）
- 列表与创建：GET /api/properties/、POST /api/properties/
- 详情、更新与删除：GET /api/properties/{id}/、PUT /api/properties/{id}/、PATCH /api/properties/{id}/、DELETE /api/properties/{id}/
- 获取可租房源: GET /api/properties/available/

字段：
- id：房产ID
- house_number：房号
- area：面积
- address：地址
- rental_status：租赁状态
- current_value：当前价值
- maintenance_status：维护状态

### 4.4 合同（Contract）
- 列表与创建：GET /api/contracts/、POST /api/contracts/
- 详情、更新与删除：GET /api/contracts/{id}/、PUT /api/contracts/{id}/、PATCH /api/contracts/{id}/、DELETE /api/contracts/{id}/

字段：
- tenant：外键，关联 Tenant 模型。
- properties：多对多关系，关联 Property 模型。
- start_date：合同开始日期。
- end_date：合同结束日期。
- monthly_rent：月租金。
- yearly_rent：年租金。
- total_rent：总租金。
- rental_area：租赁面积。
- rental_unit_price：租赁单价。
- rent_collection_time：租金收取时间。
- status：合同状态（有效、终止、过期）。
- current_receivable：当前应收金额。
- current_outstanding：当前未结金额。
- total_overdue：累计逾期金额。
- contract_file：合同文件。
- deposit_amount：保证金金额。
- management_fee：物业管理费。
- business_type：经营业态。
- rental_purpose：租赁用途。
- decoration_period：装修期（天）。
- rent_free_period：免租期（天）。
- utilities_payment：水电费支付方式。
- promotion_fee：推广费。
创建合同事例
~~~
POST /api/contracts/
{
    "tenant_id": 1,
    "property_ids": [1, 2],
    "start_date": "2024-03-01",
    "end_date": "2025-02-28",
    "monthly_rent": 2000.00,
    "yearly_rent": 24000.00,
    "total_rent": 24000.00,
    "rental_area": 120.50,
    "rental_unit_price": 16.60,
    "rent_collection_time": "2024-03-01",
    "deposit_amount": 4000.00,
    "management_fee": 500.00,
    "business_type": "零售",
    "rental_purpose": "商铺经营",
    "decoration_period": 30,
    "rent_free_period": 15,
    "utilities_payment": "按实际使用量收取",
    "promotion_fee": 1000.00
}
~~~
### 4.5 费用（Fee）
- 列表与创建：GET /api/fees/、POST /api/fees/
- 详情、更新与删除：GET /api/fees/{id}/、PUT /api/fees/{id}/、PATCH /api/fees/{id}/、DELETE /api/fees/{id}/

字段：
- id：费用ID
- contract：关联的合同（合同ID）
- category：费用类别
- amount：费用金额
- term：费用所属期
- is_collected：是否已收取
- overdue_status：是否逾期
- payment_method：支付方式
- receipt：收据文件
- bank_slip：银行凭证文件

### 4.6 支付记录（Payment）
- 列表与创建：GET /api/payments/、POST /api/payments/
- 详情、更新与删除：GET /api/payments/{id}/、PUT /api/payments/{id}/、PATCH /api/payments/{id}/、DELETE /api/payments/{id}/
- 获取应收费用列表: GET /api/payments/receivables/
- 获取欠费列表: GET /api/payments/payables/
- 打印收据: GET /api/payments/{payment_id}/print_receipt/

字段：
- id：支付ID
- fee：关联的费用（费用ID）
- payment_date：支付日期
- amount：支付金额
- payment_method：支付方式
- receipt：支付收据文件

### 4.7 数据分析（Data Analysis）
- 端点：GET /api/data-analysis/

功能：提供财务和房产的关键指标数据。

响应示例：
```
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
```
### 4.8 API总结
#### 4.8.1 主要 ViewSet API endpoints (通过 DefaultRouter 自动生成)
每个 ViewSet 都自动生成以下 CRUD 操作：

1. 租户(Tenants) API - /tenants/
- GET /tenants/ - 列出所有租户
- POST /tenants/ - 创建新租户
- GET /tenants/{id}/ - 获取特定租户
- PUT/PATCH /tenants/{id}/ - 更新租户
- DELETE /tenants/{id}/ - 删除租户

2. 物业(Properties) API - /properties/
- GET /properties/ - 列出所有物业
- POST /properties/ - 创建新物业
- GET /properties/{id}/ - 获取特定物业
- PUT/PATCH /properties/{id}/ - 更新物业
- DELETE /properties/{id}/ - 删除物业

3. 合同(Contracts) API - /contracts/
- GET /contracts/ - 列出所有合同
- POST /contracts/ - 创建新合同
- GET /contracts/{id}/ - 获取特定合同
- PUT/PATCH /contracts/{id}/ - 更新合同
- DELETE /contracts/{id}/ - 删除合同

4. 费用(Fees) API - /fees/
- GET /fees/ - 列出所有费用
- POST /fees/ - 创建新费用
- GET /fees/{id}/ - 获取特定费用
- PUT/PATCH /fees/{id}/ - 更新费用
- DELETE /fees/{id}/ - 删除费用

5. 支付(Payments) API - /payments/
- GET /payments/ - 列出所有支付
- POST /payments/ - 创建新支付
- GET /payments/{id}/ - 获取特定支付
- PUT/PATCH /payments/{id}/ - 更新支付
- DELETE /payments/{id}/ - 删除支付

#### 4.8.2 自定义 Action endpoints

支付相关的额外端点：
- GET /payments/receivables/ - 获取所有应收款项
- GET /payments/payables/ - 获取所有逾期未付款项
- GET /payments/{id}/print_receipt/ - 打印特定支付的收据
- GET /api/tenants/{d}/fees/ - 获取客户费用清单
- POST /api/tenants/{tenant_id}/send_notification/ - 发送费用通知
- GET /api/properties/available/ - 获取可租房源

#### 4.8.3 数据分析 endpoint

- GET /data-analysis/ - 获取系统综合数据分析，包括:
  - 财务数据 (应收金额、已收金额、逾期金额、收款率)
  - 物业数据 (总面积、已租面积、可用物业数量、出租率)

## 5. 认证与权限

项目使用 Django REST Framework (DRF) 提供的认证机制。默认情况下，所有 API 端点都需要经过认证才能访问。

### 5.1 认证方式
- Token-Based Authentication：建议使用 DRF 的 Token Authentication 或 JWT（JSON Web Token）进行认证，以便前端通过令牌与后端进行通信。

### 5.1 JWT认证流程

1. **获取令牌**
```http
POST /api/token/
Content-Type: application/json

{
    "username": "your_username",
    "password": "your_password"
}
```

成功响应：
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

2. **使用访问令牌**
在所有API请求的Header中添加：
```http
Authorization: Bearer <access_token>
```

3. **刷新令牌**
当access token过期时，使用refresh token获取新的access token：
```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token"
}
```

成功响应：
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### 5.2 前端实现示例

```javascript
// API配置
const API_URL = 'http://localhost:8000';

// 登录函数
async function login(username, password) {
    try {
        const response = await fetch(`${API_URL}/api/token/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username,
                password,
            }),
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        // 存储令牌
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        
        return data;
    } catch (error) {
        console.error('Login error:', error);
        throw error;
    }
}

// API请求拦截器示例
async function apiRequest(url, options = {}) {
    const accessToken = localStorage.getItem('access_token');
    
    // 添加认证头
    options.headers = {
        ...options.headers,
        'Authorization': `Bearer ${accessToken}`,
    };

    try {
        const response = await fetch(`${API_URL}${url}`, options);
        
        if (response.status === 401) {
            // 令牌过期，尝试刷新
            const newToken = await refreshToken();
            if (newToken) {
                // 使用新令牌重试请求
                options.headers['Authorization'] = `Bearer ${newToken}`;
                return await fetch(`${API_URL}${url}`, options);
            }
        }
        
        return response;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// 令牌刷新函数
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    try {
        const response = await fetch(`${API_URL}/api/token/refresh/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                refresh: refreshToken,
            }),
        });

        if (!response.ok) {
            throw new Error('Token refresh failed');
        }

        const data = await response.json();
        localStorage.setItem('access_token', data.access);
        return data.access;
    } catch (error) {
        // 刷新失败，清除令牌并重定向到登录页
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return null;
    }
}

// 使用示例
async function fetchUserData() {
    try {
        const response = await apiRequest('/api/user/profile/');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Failed to fetch user data:', error);
        throw error;
    }
}
```

### 5.3 注意事项

1. **令牌存储**
   - 将令牌存储在 localStorage 中（如上示例）或更安全的方式（如 HttpOnly Cookie）
   - 注意在用户登出时清除存储的令牌

2. **令牌刷新策略**
   - access token 有效期为1小时
   - refresh token 有效期为7天
   - 建议在收到401响应时自动尝试刷新令牌

3. **安全建议**
   - 使用HTTPS传输
   - 定期刷新令牌
   - 在用户登出时使令牌失效

### 5.2 权限设置
- IsAuthenticated：仅允许已认证用户访问 API 端点。
- 自定义权限（可选）：根据角色（如管理员、普通用户等）设置不同的访问权限。

示例权限配置：
```python
# rental_management/settings.py

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',  # 或 'rest_framework_simplejwt.authentication.JWTAuthentication'
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```
## 6. Celery 任务

项目使用 Celery 处理异步任务，主要用于定时发送缴费通知和逾期通知邮件。

### 6.1 配置
```python
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
```
### 6.2 任务定义
```python
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
```
### 6.3 启动 Celery

需要同时启动 Celery Worker 和 Celery Beat：
- 终端 1：启动 Celery Worker
```
celery -A rental_management worker -l info
```

- 终端 2：启动 Celery Beat
```
celery -A rental_management beat -l info
```
## 7. 邮件模板

项目使用 Django 的模板系统来生成邮件内容，位于 templates/emails/ 目录下。

### 7.1 缴费通知模板
```
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
```
### 7.2 逾期缴费通知模板
```
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
```
## 8. 开发环境设置

以下是项目的开发环境设置指南，确保前端开发人员能够顺利与后端进行集成。

### 8.1 环境要求
- Python：3.12
- 虚拟环境管理：Anaconda
- 数据库：PostgreSQL
- 消息中间件：Redis
- 依赖管理：requirements.txt

### 8.2 环境配置步骤
1.	克隆项目仓库
```
git clone https://github.com/your-repo/rental_management.git
cd rental_management
```
2.	创建并激活 Anaconda 虚拟环境
~~~
conda create -n managest python=3.12
conda activate managest
~~~
3.	安装依赖
~~~
pip install --upgrade pip
pip install -r requirements.txt
~~~
4.	配置数据库
确保 PostgreSQL 已安装并运行，创建数据库和用户：
~~~
CREATE DATABASE rental_db;
CREATE USER rental_user WITH PASSWORD 'rental_password';
GRANT ALL PRIVILEGES ON DATABASE rental_db TO rental_user;
~~~
5.	配置 Redis
确保 Redis 已安装并运行：
~~~
brew install redis  # macOS 使用 Homebrew 安装
brew services start redis
redis-cli ping
# 预期输出: PONG
~~~
6.	配置环境变量
在 rental_management/settings.py 中，设置数据库、Celery、邮件等相关配置：
~~~
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
~~~
7.	运行数据库迁移
~~~
python manage.py makemigrations rental_app
python manage.py migrate
~~~
8.	创建超级用户
~~~
python manage.py createsuperuser
~~~
9.	启动 Celery Worker 和 Celery Beat
- 终端 1：
~~~
celery -A rental_management worker -l info
~~~
- 终端 2：
~~~
celery -A rental_management beat -l info
~~~
10.	启动 Django 开发服务器
~~~
python manage.py runserver
~~~
11.	访问管理后台
打开浏览器，访问 
http://localhost:8000/admin/，
使用超级用户账号登录。

