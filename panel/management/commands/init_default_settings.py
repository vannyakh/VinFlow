from django.core.management.base import BaseCommand
from panel.models import SystemSetting

class Command(BaseCommand):
    help = 'Initialize default system settings'

    def handle(self, *args, **options):
        default_settings = [
            # General Settings
            {
                'key': 'site_name',
                'label': 'Site Name',
                'setting_type': 'text',
                'group': 'general',
                'default_value': 'VinFlow SMM Panel',
                'description': 'The name of your SMM panel',
                'order': 1,
            },
            {
                'key': 'site_logo',
                'label': 'Site Logo',
                'setting_type': 'image',
                'group': 'general',
                'default_value': '',
                'description': 'Site logo image (upload or enter URL/path)',
                'order': 2,
            },
            {
                'key': 'site_description',
                'label': 'Site Description',
                'setting_type': 'textarea',
                'group': 'general',
                'default_value': 'Professional SMM Panel for Social Media Marketing',
                'description': 'Site meta description for SEO',
                'order': 3,
            },
            {
                'key': 'site_email',
                'label': 'Site Email',
                'setting_type': 'email',
                'group': 'general',
                'default_value': 'admin@vinflow.com',
                'description': 'Main contact email address',
                'order': 4,
            },
            {
                'key': 'min_deposit',
                'label': 'Minimum Deposit',
                'setting_type': 'number',
                'group': 'payment',
                'default_value': '5.00',
                'description': 'Minimum deposit amount',
                'order': 1,
            },
            {
                'key': 'max_deposit',
                'label': 'Maximum Deposit',
                'setting_type': 'number',
                'group': 'payment',
                'default_value': '10000.00',
                'description': 'Maximum deposit amount',
                'order': 2,
            },
            {
                'key': 'currency',
                'label': 'Currency',
                'setting_type': 'text',
                'group': 'payment',
                'default_value': 'USD',
                'description': 'Default currency code',
                'order': 3,
            },
            {
                'key': 'currency_symbol',
                'label': 'Currency Symbol',
                'setting_type': 'text',
                'group': 'payment',
                'default_value': '$',
                'description': 'Currency symbol',
                'order': 4,
            },
            {
                'key': 'enable_registration',
                'label': 'Enable Registration',
                'setting_type': 'boolean',
                'group': 'security',
                'default_value': 'true',
                'description': 'Allow new user registration',
                'order': 1,
            },
            {
                'key': 'require_email_verification',
                'label': 'Require Email Verification',
                'setting_type': 'boolean',
                'group': 'security',
                'default_value': 'false',
                'description': 'Require email verification for new accounts',
                'order': 2,
            },
            {
                'key': 'maintenance_mode',
                'label': 'Maintenance Mode',
                'setting_type': 'boolean',
                'group': 'maintenance',
                'default_value': 'false',
                'description': 'Enable maintenance mode',
                'order': 1,
            },
            {
                'key': 'maintenance_message',
                'label': 'Maintenance Message',
                'setting_type': 'textarea',
                'group': 'maintenance',
                'default_value': 'We are currently performing maintenance. Please check back soon.',
                'description': 'Message to display during maintenance',
                'order': 2,
            },
            {
                'key': 'api_enabled',
                'label': 'API Enabled',
                'setting_type': 'boolean',
                'group': 'api',
                'default_value': 'true',
                'description': 'Enable API access',
                'is_public': True,
                'order': 1,
            },
            {
                'key': 'api_rate_limit',
                'label': 'API Rate Limit',
                'setting_type': 'number',
                'group': 'api',
                'default_value': '100',
                'description': 'API requests per minute',
                'order': 2,
            },
            # SMM Service Supplier Settings
            {
                'key': 'supplier_jap_url',
                'label': 'JAP API URL',
                'setting_type': 'url',
                'group': 'api',
                'default_value': 'https://justanotherpanel.com/api/v2',
                'description': 'JustAnotherPanel API endpoint URL',
                'order': 10,
            },
            {
                'key': 'supplier_jap_key',
                'label': 'JAP API Key',
                'setting_type': 'text',
                'group': 'api',
                'default_value': '',
                'description': 'JustAnotherPanel API key',
                'is_encrypted': True,
                'order': 11,
            },
            {
                'key': 'supplier_peakerr_url',
                'label': 'Peakerr API URL',
                'setting_type': 'url',
                'group': 'api',
                'default_value': 'https://peakerr.com/api/v2',
                'description': 'Peakerr API endpoint URL',
                'order': 12,
            },
            {
                'key': 'supplier_peakerr_key',
                'label': 'Peakerr API Key',
                'setting_type': 'text',
                'group': 'api',
                'default_value': '',
                'description': 'Peakerr API key',
                'is_encrypted': True,
                'order': 13,
            },
            {
                'key': 'supplier_smmkings_url',
                'label': 'SMMKings API URL',
                'setting_type': 'url',
                'group': 'api',
                'default_value': 'https://smmkings.com/api/v2',
                'description': 'SMMKings API endpoint URL',
                'order': 14,
            },
            {
                'key': 'supplier_smmkings_key',
                'label': 'SMMKings API Key',
                'setting_type': 'text',
                'group': 'api',
                'default_value': '',
                'description': 'SMMKings API key',
                'is_encrypted': True,
                'order': 15,
            },
            {
                'key': 'supplier_timeout',
                'label': 'Supplier API Timeout',
                'setting_type': 'number',
                'group': 'api',
                'default_value': '30',
                'description': 'Timeout in seconds for supplier API requests',
                'order': 16,
            },
            {
                'key': 'supplier_retry_attempts',
                'label': 'Supplier Retry Attempts',
                'setting_type': 'number',
                'group': 'api',
                'default_value': '3',
                'description': 'Number of retry attempts for failed supplier API calls',
                'order': 17,
            },
            {
                'key': 'auto_sync_order_status',
                'label': 'Auto Sync Order Status',
                'setting_type': 'boolean',
                'group': 'api',
                'default_value': 'true',
                'description': 'Automatically sync order status from suppliers',
                'order': 18,
            },
            {
                'key': 'sync_interval_minutes',
                'label': 'Order Status Sync Interval',
                'setting_type': 'number',
                'group': 'api',
                'default_value': '5',
                'description': 'Interval in minutes for syncing order status',
                'order': 19,
            },
        ]

        created_count = 0
        updated_count = 0

        for setting_data in default_settings:
            key = setting_data.pop('key')
            setting, created = SystemSetting.objects.get_or_create(
                key=key,
                defaults=setting_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created setting: {key}'))
            else:
                # Update existing settings with new defaults if they don't have values
                if not setting.value and setting_data.get('default_value'):
                    setting.value = setting_data['default_value']
                    setting.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'Updated setting: {key}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully initialized settings: {created_count} created, {updated_count} updated'
            )
        )

