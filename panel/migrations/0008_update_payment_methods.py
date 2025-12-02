# Generated migration for updating payment methods

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0007_alter_systemsetting_setting_type_notification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(
                choices=[
                    ('paypal', 'PayPal'),
                    ('stripe', 'Stripe'),
                    ('khqr', 'KHQR Bakong')
                ],
                max_length=20
            ),
        ),
    ]

