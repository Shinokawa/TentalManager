# rental_app/views.py

from rest_framework import viewsets, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.db.models import Sum
from django.core.files import File  # 添加这行导入
from django.http import FileResponse, HttpResponseServerError
import os
import logging
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from .models import Tenant, Property, Contract, Fee, Payment
from .serializers import (
    TenantSerializer, PropertySerializer,
    ContractSerializer, FeeSerializer, PaymentSerializer
)
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status  # 添加这行导入
from rest_framework.exceptions import ValidationError  # 添加这行导入

logger = logging.getLogger(__name__)

class TenantViewSet(viewsets.ModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def fees(self, request, pk=None):
        """获取指定租户的所有费用清单"""
        tenant = self.get_object()
        fees = Fee.objects.filter(
            contract__tenant=tenant
        ).select_related(
            'contract'
        ).order_by(
            '-contract__start_date', 
            'category'
        )
        
        serializer = FeeSerializer(fees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_notification(self, request, pk=None):
        """向租户发送未缴费用通知"""
        tenant = self.get_object()
        unpaid_fees = Fee.objects.filter(
            contract__tenant=tenant,
            is_collected=False
        )
        
        if not unpaid_fees.exists():
            return Response({
                "message": "该租户没有未缴费用"
            }, status=400)

        # 计算总未付金额
        total_amount = sum(fee.amount for fee in unpaid_fees)
        
        # 发送邮件通知
        subject = '费用缴纳提醒'
        message = f"""
        尊敬的{tenant.first_name} {tenant.last_name}：
        
        您目前有 {unpaid_fees.count()} 笔费用尚未支付，总金额：¥{total_amount}。
        请及时缴纳以下费用：
        
        {chr(10).join([f"- {fee.category}: ¥{fee.amount} ({fee.term})" for fee in unpaid_fees])}
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=False,
            )
            
            return Response({
                "message": f"已成功向租户 {tenant.first_name} {tenant.last_name} 发送费用通知",
                "unpaid_fees_count": unpaid_fees.count(),
                "total_amount": total_amount
            })
            
        except Exception as e:
            return Response({
                "message": "发送通知失败",
                "error": str(e)
            }, status=500)

class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def available(self, request):
        available_properties = Property.objects.filter(rental_status='available')
        serializer = self.get_serializer(available_properties, many=True)
        return Response(serializer.data)

class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all().select_related('tenant').prefetch_related('properties')
    serializer_class = ContractSerializer
    permission_classes = [permissions.IsAuthenticated]

class FeeViewSet(viewsets.ModelViewSet):
    queryset = Fee.objects.all().select_related('contract')
    serializer_class = FeeSerializer
    permission_classes = [permissions.IsAuthenticated]

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('fee__contract')
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Payment.objects.all().select_related('fee__contract')
        fee_id = self.request.query_params.get('fee', None)
        if fee_id is not None:
            queryset = queryset.filter(fee_id=fee_id)
        return queryset

    @action(detail=False, methods=['get'])
    def receivables(self, request):
        receivables = Fee.objects.filter(is_collected=False)
        serializer = FeeSerializer(receivables, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def payables(self, request):
        payables = Fee.objects.filter(overdue_status='overdue', is_collected=False)
        serializer = FeeSerializer(payables, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def print_receipt(self, request, pk=None):
        try:
            payment = self.get_object()
            
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            pdf_path = os.path.join(temp_dir, f'receipt_{payment.id}.pdf')
            
            # 生成PDF
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.setFont("Helvetica", 12)
            
            # 添加收据内容
            c.drawString(100, 800, f"收据编号: {payment.id}")
            c.drawString(100, 780, f"日期: {payment.payment_date.strftime('%Y-%m-%d')}")
            c.drawString(100, 760, f"支付方式: {payment.get_payment_method_display()}")
            c.drawString(100, 740, f"金额: ¥{payment.amount}")
            
            if payment.fee and payment.fee.contract:
                tenant = payment.fee.contract.tenant
                c.drawString(100, 720, f"租户: {tenant.first_name} {tenant.last_name}")
                c.drawString(100, 700, f"费用类型: {payment.fee.get_category_display()}")
                c.drawString(100, 680, f"所属期限: {payment.fee.term}")
            
            c.save()
            
            # 返回生成的PDF
            try:
                response = FileResponse(
                    open(pdf_path, 'rb'),
                    content_type='application/pdf'
                )
                response['Content-Disposition'] = f'attachment; filename="receipt_{payment.id}.pdf"'
                return response
            finally:
                # 确保文件存在才删除
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
                    
        except Exception as e:
            return HttpResponseServerError(f"生成收据失败: {str(e)}")

    def create(self, request, *args, **kwargs):
        logger.info(f"Payment request data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        
        # 检查费用是否已支付
        fee_id = request.data.get('fee_id')
        if Payment.objects.filter(fee_id=fee_id).exists():
            return Response(
                {'detail': '该费用已支付，请勿重复支付！'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not serializer.is_valid():
            logger.error(f"Payment validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        payment = serializer.save()
        fee = payment.fee
        
        # 更新费用状态
        fee.is_collected = True
        fee.payment_method = payment.payment_method
        fee.receipt = payment.receipt
        
        # 更新合同相关金额
        contract = fee.contract
        contract.current_receivable = contract.fees.filter(
            is_collected=False).aggregate(total=Sum('amount'))['total'] or 0
        contract.current_outstanding = contract.fees.filter(
            is_collected=False, overdue_status='overdue').aggregate(total=Sum('amount'))['total'] or 0
        contract.total_overdue = contract.fees.filter(
            overdue_status='overdue').aggregate(total=Sum('amount'))['total'] or 0
        
        # 保存更改
        fee.save()
        contract.save()
        
        # 尝试生成收据
        try:
            pdf_path = payment.generate_receipt()
            if pdf_path:
                with open(pdf_path, 'rb') as pdf:
                    payment.receipt.save(
                        f'receipt_{payment.id}.pdf',
                        File(pdf),
                        save=True
                    )
                os.unlink(pdf_path)  # 清理临时文件
        except Exception as e:
            logger.error(f"保存收据时发生错误: {str(e)}")
            # 继续执行，不影响支付流程

@api_view(['GET'])
def data_analysis(request):
    receivable_amount = Fee.objects.filter(is_collected=False).aggregate(total=Sum('amount'))['total'] or 0
    received_amount = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    overdue_amount = Fee.objects.filter(overdue_status='overdue', is_collected=False).aggregate(total=Sum('amount'))['total'] or 0
    collection_rate = (received_amount / receivable_amount) * 100 if receivable_amount else 0

    total_area = Property.objects.aggregate(total=Sum('area'))['total'] or 0
    rented_area = Property.objects.filter(rental_status='rented').aggregate(total=Sum('area'))['total'] or 0
    available_properties = Property.objects.filter(rental_status='available').count()
    rental_rate = (rented_area / total_area) * 100 if total_area else 0

    data = {
        'financial': {
            'receivable_amount': receivable_amount,
            'received_amount': received_amount,
            'overdue_amount': overdue_amount,
            'collection_rate': collection_rate,
        },
        'property': {
            'total_area': total_area,
            'rented_area': rented_area,
            'available_properties': available_properties,
            'rental_rate': rental_rate,
        }
    }
    return Response(data)