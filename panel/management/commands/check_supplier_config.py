from django.core.management.base import BaseCommand
from django.conf import settings
from panel.settings_utils import get_setting
from panel.models import Order, SystemSetting
import requests


class Command(BaseCommand):
    help = 'Check supplier API configuration and test connection'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n' + '='*60))
        self.stdout.write(self.style.WARNING('SUPPLIER API CONFIGURATION CHECK'))
        self.stdout.write(self.style.WARNING('='*60 + '\n'))

        # Check JAP API settings
        jap_url = get_setting('supplier_jap_url', 'https://justanotherpanel.com/api/v2')
        jap_key = get_setting('supplier_jap_key', getattr(settings, 'JAP_API_KEY', ''))
        timeout = int(get_setting('supplier_timeout', '30'))
        retry_attempts = int(get_setting('supplier_retry_attempts', '3'))

        self.stdout.write(f'📍 API URL: {jap_url}')
        
        if jap_key:
            masked_key = jap_key[:8] + '*' * (len(jap_key) - 12) + jap_key[-4:] if len(jap_key) > 12 else '*' * len(jap_key)
            self.stdout.write(self.style.SUCCESS(f'✅ API Key: {masked_key} (Configured)'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ API Key: NOT CONFIGURED'))
            self.stdout.write(self.style.ERROR('\n⚠️  CRITICAL: Supplier API key is missing!'))
            self.stdout.write(self.style.WARNING('\nTo fix this, you need to:'))
            self.stdout.write(self.style.WARNING('1. Get your API key from JustAnotherPanel.com'))
            self.stdout.write(self.style.WARNING('2. Go to Admin Panel → Settings → API Settings'))
            self.stdout.write(self.style.WARNING('3. Enter your JAP API Key'))
            self.stdout.write(self.style.WARNING('4. Click Save'))
            self.stdout.write(self.style.WARNING('\nOR set it in your .env file:'))
            self.stdout.write(self.style.WARNING('JAP_API_KEY=your_api_key_here\n'))
            return

        self.stdout.write(f'⏱️  Timeout: {timeout} seconds')
        self.stdout.write(f'🔄 Retry Attempts: {retry_attempts}\n')

        # Test API connection
        self.stdout.write(self.style.WARNING('Testing API connection...\n'))

        try:
            # Test with balance check action
            payload = {
                'key': jap_key,
                'action': 'balance'
            }

            response = requests.post(jap_url, data=payload, timeout=10)
            data = response.json()

            if response.status_code == 200:
                if 'balance' in data:
                    self.stdout.write(self.style.SUCCESS(f'✅ API Connection: SUCCESS'))
                    self.stdout.write(self.style.SUCCESS(f'💰 Supplier Balance: ${data["balance"]}'))
                    self.stdout.write(self.style.SUCCESS(f'💵 Currency: {data.get("currency", "USD")}\n'))
                elif 'error' in data:
                    self.stdout.write(self.style.ERROR(f'❌ API Error: {data["error"]}'))
                    self.stdout.write(self.style.ERROR('\nPlease check your API key is correct.\n'))
                else:
                    self.stdout.write(self.style.WARNING(f'⚠️  Unexpected response: {data}\n'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ HTTP Error: {response.status_code}'))
                self.stdout.write(self.style.ERROR(f'Response: {data}\n'))

        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR('❌ Connection timed out'))
            self.stdout.write(self.style.ERROR('The supplier API is not responding.\n'))
        except requests.exceptions.ConnectionError:
            self.stdout.write(self.style.ERROR('❌ Connection failed'))
            self.stdout.write(self.style.ERROR('Cannot connect to supplier API. Check your internet connection.\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}\n'))

        # Check pending orders
        pending_orders = Order.objects.filter(status='Pending').count()
        processing_orders = Order.objects.filter(status='Processing').count()

        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('ORDER STATUS SUMMARY'))
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(f'⏳ Pending Orders: {pending_orders}')
        self.stdout.write(f'🔄 Processing Orders: {processing_orders}')

        if pending_orders > 0:
            self.stdout.write(self.style.WARNING(f'\n⚠️  You have {pending_orders} pending orders waiting to be sent to supplier.'))
            self.stdout.write(self.style.WARNING('These orders may need to be retried if the API was down.\n'))

        # Check if OrderLog table exists and has entries
        try:
            from panel.models import OrderLog
            recent_logs = OrderLog.objects.filter(log_type__in=['api_call', 'api_response', 'error']).order_by('-created_at')[:5]
            
            if recent_logs.exists():
                self.stdout.write(self.style.WARNING('\n' + '='*60))
                self.stdout.write(self.style.WARNING('RECENT API ACTIVITY LOGS'))
                self.stdout.write(self.style.WARNING('='*60))
                for log in recent_logs:
                    icon = '🔵' if log.log_type == 'api_call' else '🟢' if log.log_type == 'api_response' else '🔴'
                    self.stdout.write(f'{icon} [{log.created_at.strftime("%Y-%m-%d %H:%M:%S")}] {log.message}')
                self.stdout.write('')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'\nℹ️  Order logs not available: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Configuration check complete!\n'))

