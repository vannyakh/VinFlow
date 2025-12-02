# VinFlow SMM Panel

A beautiful, fast SMM (Social Media Marketing) dashboard panel built with Django, HTMX, and Tailwind CSS.

## Features

✅ **Multi-language Support** - Khmer (ភាសាខ្មែរ) and English with one-click toggle  
✅ **5000+ Services Auto-Sync** - Instagram, TikTok, Facebook, YouTube, Twitter, Shopee, Telegram  
✅ **Drip-Feed Orders** - Spread orders over days for natural growth  
✅ **Mass Order Upload** - Upload 100+ links via CSV/Excel  
✅ **Refill System** - Auto or manual refill (30-360 days)  
✅ **Child Panel / Reseller System** - White-label solution  
✅ **Subscription Packages** - Auto daily/monthly delivery  
✅ **Full JSON API** - For resellers to integrate  
✅ **Real-Time Order Tracking** - HTMX polling every 60 seconds  
✅ **Ticket Support System** - User tickets with admin replies  
✅ **Multiple Payment Gateways** - ABA PayWay, Wing, Pi Pay, KHQR, USDT, Credit Card  
✅ **Coupon & Discount System** - Flexible discount codes  
✅ **Beautiful Dark Dashboard** - Purple-cyan-gold theme  
✅ **Mobile-First & PWA** - Install as app on phone  
✅ **Admin Statistics & Charts** - Daily orders, revenue, top services  
✅ **User Roles** - Admin / Reseller / User with permissions  
✅ **Fraud Prevention** - Auto-detect fake links + refund system  
✅ **SEO Ready + Blog** - Built-in blog system  
✅ **One-Click Service Import** - Import from JustAnotherPanel, Peakerr, SMMKings  
✅ **Free Trial** - 100 free likes for new users  

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL
- Redis (for Celery)
- Node.js (optional, for Tailwind build)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd VinFlow
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure database in `core/settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vinflow_db',
        'USER': 'your_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

5. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Create superuser:
```bash
python manage.py createsuperuser
```

7. Start Redis:
```bash
redis-server
```

8. Start Celery worker (in separate terminal):
```bash
celery -A core worker -l info
```

9. Compile translation messages:
```bash
python manage.py compilemessages
```

10. Start development server:
```bash
python manage.py runserver
```

## Translation Management

### Update Translations

1. Extract translatable strings:
```bash
python manage.py makemessages -l en -l km
```

2. Edit translation files:
- `locale/en/LC_MESSAGES/django.po` (English)
- `locale/km/LC_MESSAGES/django.po` (Khmer)

3. Compile translations:
```bash
python manage.py compilemessages
```

### Using Translations in Templates

Use `{% trans %}` for simple strings:
```django
{% load i18n %}
<h1>{% trans "Welcome to VinFlow" %}</h1>
```

Use `{% blocktrans %}` for strings with variables:
```django
{% blocktrans with username=user.username %}Welcome, {{ username }}!{% endblocktrans %}
```

## Configuration

### Supplier API Keys

Add to `core/settings.py`:
```python
JAP_API_KEY = 'your_justanotherpanel_api_key'
PEAKERR_API_KEY = 'your_peakerr_api_key'
SMMKINGS_API_KEY = 'your_smmkings_api_key'
```

### Celery Configuration

Ensure Redis is running and configured in `core/settings.py`:
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

## Usage

### Creating Orders

1. Navigate to Services page
2. Select a service
3. Enter link and quantity
4. Optionally enable drip-feed
5. Apply coupon code if available
6. Submit order

### Mass Order Upload

1. Prepare CSV file with columns: `service_id`, `link`, `quantity`
2. Go to Orders page
3. Click "Mass Order (CSV)"
4. Upload CSV file

### API Usage

#### Login
```bash
POST /api/login/
{
    "username": "your_username",
    "password": "your_password"
}
```

#### Get Services
```bash
GET /api/services/
Headers: Authorization: Token your_token_here
```

#### Create Order
```bash
POST /api/orders/
Headers: Authorization: Token your_token_here
{
    "service_id": 1,
    "link": "https://instagram.com/p/...",
    "quantity": 1000,
    "drip_feed": false,
    "coupon_code": "VINOPENING"
}
```

## Project Structure

```
VinFlow/
├── core/           # Django project settings
├── panel/          # Main app
│   ├── models.py   # Database models
│   ├── views.py    # View functions
│   ├── api_views.py # API endpoints
│   ├── tasks.py    # Celery tasks
│   └── admin.py    # Django admin
├── templates/      # HTML templates
│   └── panel/      # Panel templates
├── static/         # Static files
└── locale/         # Translation files
```

## Features in Detail

### Multi-language
- One-click toggle between Khmer and English
- All UI elements translated
- Uses Django i18n framework

### Real-Time Updates
- HTMX polling for order status
- Updates every 60 seconds
- No page refresh needed

### Drip-Feed
- Spread large orders over multiple days
- Example: 10k followers → 500/day for 20 days
- Looks natural and organic

### Subscription Packages
- Auto daily/monthly delivery
- Perfect for TikTok shops
- Set and forget

### Reseller System
- White-label child panels
- Custom domains
- Full API access

## License

Proprietary - All rights reserved

## Support

For support, create a ticket in the dashboard or contact admin.

