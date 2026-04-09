"""
支付定时任务
实现支付状态同步和归档的定时任务
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from payments.services.payment_service import payment_service
from payments.config import PAYMENT_CONFIG

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '支付定时任务：同步支付状态和归档支付记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='同步支付状态',
        )
        parser.add_argument(
            '--archive',
            action='store_true',
            help='归档支付记录',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=PAYMENT_CONFIG['archive_days'],
            help='归档天数（默认90天）',
        )

    def handle(self, *args, **options):
        sync = options.get('sync', False)
        archive = options.get('archive', False)
        days = options.get('days', PAYMENT_CONFIG['archive_days'])

        self.stdout.write(self.style.SUCCESS(f'开始执行支付定时任务 - {timezone.now()}'))

        # 如果没有指定任何选项，则执行所有任务
        if not sync and not archive:
            sync = True
            archive = True

        # 同步支付状态
        if sync:
            self.stdout.write('开始同步支付状态...')
            try:
                payment_service.sync_pending_payments()
                self.stdout.write(self.style.SUCCESS('支付状态同步完成'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'支付状态同步失败: {str(e)}'))
                logger.error(f'支付状态同步失败: {str(e)}', exc_info=True)

        # 归档支付记录
        if archive:
            self.stdout.write(f'开始归档支付记录（{days}天前）...')
            try:
                result = payment_service.archive_payment_records(days)
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(f"支付记录归档完成，共归档 {result['count']} 条记录"))
                else:
                    self.stdout.write(self.style.ERROR(f"支付记录归档失败: {result['message']}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'支付记录归档失败: {str(e)}'))
                logger.error(f'支付记录归档失败: {str(e)}', exc_info=True)

        self.stdout.write(self.style.SUCCESS(f'支付定时任务执行完成 - {timezone.now()}'))