from django.core.management.base import BaseCommand
from panel.models import Order
from panel.tasks import place_order_to_supplier, execute_task_async_or_sync
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = 'Retry sending pending orders to supplier'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=str,
            help='Retry a specific order by order_id (e.g., ORD-12345)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Retry all pending orders',
        )
        parser.add_argument(
            '--recent',
            type=int,
            default=24,
            help='Retry orders from the last N hours (default: 24)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('RETRY PENDING ORDERS'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))

        if options['order_id']:
            # Retry specific order
            try:
                order = Order.objects.get(order_id=options['order_id'])
                self.stdout.write(f'Found order: {order.order_id}')
                self.stdout.write(f'Status: {order.status}')
                self.stdout.write(f'Service: {order.service.name}')
                self.stdout.write(f'User: {order.user.username}')
                self.stdout.write(f'Created: {order.created_at}\n')

                if order.status == 'Processing':
                    self.stdout.write(self.style.WARNING('⚠️  This order is already processing. Skip retry? (y/n)'))
                    response = input()
                    if response.lower() != 'y':
                        self.stdout.write(self.style.WARNING('Skipped.\n'))
                        return

                self.stdout.write('Retrying order...')
                execute_task_async_or_sync(place_order_to_supplier, order.id)
                self.stdout.write(self.style.SUCCESS(f'✅ Order {order.order_id} queued for retry!\n'))

            except Order.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Order {options["order_id"]} not found.\n'))
                return

        elif options['all']:
            # Retry all pending orders
            pending_orders = Order.objects.filter(status='Pending')
            count = pending_orders.count()

            if count == 0:
                self.stdout.write(self.style.SUCCESS('✅ No pending orders found.\n'))
                return

            self.stdout.write(self.style.WARNING(f'Found {count} pending orders.'))
            self.stdout.write(self.style.WARNING(f'⚠️  Are you sure you want to retry all {count} orders? (y/n)'))
            response = input()

            if response.lower() == 'y':
                success_count = 0
                for order in pending_orders:
                    try:
                        execute_task_async_or_sync(place_order_to_supplier, order.id)
                        self.stdout.write(f'✅ Queued: {order.order_id}')
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'❌ Failed to queue {order.order_id}: {str(e)}'))

                self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully queued {success_count}/{count} orders for retry!\n'))
            else:
                self.stdout.write(self.style.WARNING('Cancelled.\n'))

        else:
            # Retry orders from last N hours
            hours = options['recent']
            time_threshold = timezone.now() - timedelta(hours=hours)
            pending_orders = Order.objects.filter(
                status='Pending',
                created_at__gte=time_threshold
            )
            count = pending_orders.count()

            if count == 0:
                self.stdout.write(self.style.SUCCESS(f'✅ No pending orders from the last {hours} hours.\n'))
                return

            self.stdout.write(f'Found {count} pending orders from the last {hours} hours:\n')
            for order in pending_orders[:10]:  # Show first 10
                self.stdout.write(f'  • {order.order_id} - {order.service.name} - {order.created_at.strftime("%Y-%m-%d %H:%M")}')

            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more\n')
            else:
                self.stdout.write('')

            self.stdout.write(self.style.WARNING(f'Retry these {count} orders? (y/n)'))
            response = input()

            if response.lower() == 'y':
                success_count = 0
                for order in pending_orders:
                    try:
                        execute_task_async_or_sync(place_order_to_supplier, order.id)
                        self.stdout.write(f'✅ Queued: {order.order_id}')
                        success_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'❌ Failed to queue {order.order_id}: {str(e)}'))

                self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully queued {success_count}/{count} orders for retry!\n'))
            else:
                self.stdout.write(self.style.WARNING('Cancelled.\n'))

