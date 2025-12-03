# Marketing Promotion & Admin Management Service

## Overview
This document describes the comprehensive Marketing Promotion and Admin Management Service added to VinFlow. This system allows administrators to create, manage, and track marketing campaigns and promotions to boost user engagement and sales.

## Features

### 1. Promotion Types
The system supports multiple types of promotions:
- **Banner**: Display promotional banners on pages
- **Popup**: Show promotional popups to users
- **Notification**: Send in-app notifications about promotions
- **Email Campaign**: Send promotional emails to targeted users
- **Discount Campaign**: Offer discount codes to users
- **Flash Sale**: Time-limited special offers
- **Free Bonus**: Give free balance bonuses to users

### 2. Promotion Management

#### Promotion States
- **Draft**: Promotion is being created/edited
- **Scheduled**: Promotion is scheduled to run in the future
- **Active**: Promotion is currently running
- **Paused**: Promotion is temporarily paused
- **Completed**: Promotion has ended successfully
- **Cancelled**: Promotion was cancelled

#### Targeting Options
Promotions can be targeted to specific user segments:
- **All Users**: Show to everyone
- **New Users**: Users registered within the last 7 days
- **Active Users**: Users who have made purchases
- **Inactive Users**: Users who haven't made purchases
- **High Spenders**: Users who spent $100 or more
- **Resellers**: Only reseller accounts
- **Specific Users**: Manually selected users

#### Display Locations
- **Homepage**: Landing page for visitors
- **Dashboard**: User dashboard after login
- **Services**: Services listing page
- **Checkout**: During order/payment process
- **All Pages**: Show on every page

### 3. Promotion Settings

New system settings have been added to control promotion behavior:

```python
# Marketing Settings
marketing_enabled = True                    # Enable/disable marketing system
promotions_auto_display = True             # Auto display active promotions
promotion_popup_delay = 3                  # Delay in seconds before showing popup
promotion_max_per_page = 3                 # Max promotions per page
first_order_discount = 10                  # First order discount percentage
referral_bonus_amount = 5.00               # Referral bonus amount
new_user_welcome_bonus = 0.00              # Welcome bonus for new users
flash_sale_notification = True             # Send flash sale notifications
promotional_email_enabled = True           # Allow promotional emails
promotional_email_frequency = 7            # Days between promotional emails
```

### 4. Database Models

#### MarketingPromotion
Main model for storing promotion details:
- Basic info: title, description (English & Khmer)
- Visual elements: banner images, colors
- Targeting: audience, display location
- Scheduling: start/end dates, priority
- Call to action: button text and link
- Offer details: discount code, percentage, bonus amount
- Performance tracking: views, clicks, conversions
- Settings: auto-expire, countdown timer, max views per user

#### PromotionView
Tracks individual user views of promotions:
- Which promotion was viewed
- User who viewed (if authenticated)
- IP address and user agent
- Timestamp

#### PromotionClick
Tracks clicks on promotions:
- Which promotion was clicked
- User who clicked (if authenticated)
- IP address
- Timestamp

#### PromotionConversion
Tracks conversions from promotions:
- Conversion types: order, deposit, signup, coupon_used
- Conversion value (order amount, deposit amount)
- Linked order or payment record
- Timestamp

### 5. Admin Interface

#### Promotion List View
Path: `/admin/promotions/`
- View all promotions with filtering and search
- Filter by status, type, target audience
- Quick edit status and active state
- Pagination support

#### Create Promotion
Path: `/admin/promotions/create/`
- Form to create new promotion
- Upload banner images (desktop and mobile)
- Set targeting and scheduling
- Configure call to action
- Set offer details (discounts, bonuses)

#### Edit Promotion
Path: `/admin/promotions/<promotion_id>/edit/`
- Update existing promotion
- All fields editable
- Preview promotion before activating

#### Analytics Dashboard
Path: `/admin/promotions/<promotion_id>/analytics/`
- Detailed performance metrics
- View counts, click-through rate (CTR)
- Conversion rate and total conversion value
- Daily breakdown charts (last 30 days)
- Recent views, clicks, and conversions
- User engagement details

#### Delete Promotion
Path: `/admin/promotions/<promotion_id>/delete/` (POST)
- Soft delete promotion
- Confirmation required

### 6. Tracking Endpoints

#### Track View
**Endpoint**: `POST /promotions/track-view/`
**Parameters**: 
- `promotion_id`: ID of the promotion

Automatically tracks when a user views a promotion. Respects max_views_per_user setting.

#### Track Click
**Endpoint**: `POST /promotions/track-click/`
**Parameters**:
- `promotion_id`: ID of the promotion

Tracks when a user clicks on a promotion CTA button.

#### Get Active Promotions
**Endpoint**: `GET /promotions/active/?location=homepage`
**Parameters**:
- `location`: Page location (homepage, dashboard, services, checkout, all_pages)

Returns JSON list of currently active promotions for the specified location, filtered by target audience.

**Response**:
```json
{
  "promotions": [
    {
      "promotion_id": "PROMO12345678",
      "title": "Special Offer",
      "title_km": "ការផ្តល់ជូនពិសេស",
      "description": "Get 20% off on all services!",
      "description_km": "ទទួលបានការបញ្ចុះតម្លៃ 20% លើសេវាកម្មទាំងអស់!",
      "promotion_type": "banner",
      "banner_image": "/media/promotions/banners/banner.jpg",
      "background_color": "#007bff",
      "text_color": "#ffffff",
      "cta_text": "Shop Now",
      "cta_link": "/services/",
      "show_countdown": true,
      "end_date": "2025-12-31T23:59:59Z"
    }
  ]
}
```

### 7. Automated Tasks (Celery)

#### check_and_expire_promotions
**Schedule**: Every hour
**Function**: 
- Automatically expires promotions that have passed their end_date
- Activates scheduled promotions when their start_date arrives
- Sends notifications to promotion creators

#### send_promotional_notifications
**Schedule**: Daily
**Function**:
- Sends notifications about active flash sales
- Targets specific user segments based on promotion settings
- Respects promotional email frequency settings
- Limits to 100 users per batch to avoid spam

#### apply_welcome_bonus_for_new_users
**Schedule**: Every 10 minutes
**Function**:
- Checks for new users registered in last 24 hours
- Applies welcome bonus if enabled and user hasn't received it
- Creates payment record for tracking
- Sends welcome notification to user

#### generate_promotion_report
**Schedule**: Weekly
**Function**:
- Generates comprehensive performance report
- Calculates total views, clicks, conversions
- Computes CTR and conversion rates
- Sends summary to admin users via notifications

### 8. Performance Metrics

#### Click-Through Rate (CTR)
```python
CTR = (clicks / views) × 100
```

#### Conversion Rate
```python
Conversion Rate = (conversions / clicks) × 100
```

#### Total Conversion Value
Sum of all conversion values (order amounts, deposits) generated through the promotion.

### 9. Integration Points

#### Order Creation
When a user creates an order through a promotion:
1. Track the conversion
2. Link to the promotion
3. Record conversion value

#### Payment Completion
When a payment is completed:
1. If user came from promotion, track conversion
2. Record payment amount as conversion value

#### User Registration
When a new user registers:
1. Check if referred by promotion
2. Apply welcome bonus if enabled
3. Track signup conversion

### 10. Usage Examples

#### Creating a Flash Sale
1. Go to `/admin/promotions/create/`
2. Set title: "Flash Sale - 50% Off!"
3. Select promotion type: "Flash Sale"
4. Set target audience: "All Users"
5. Set display location: "All Pages"
6. Upload banner image
7. Set start/end dates (24 hour window)
8. Set discount percentage: 50%
9. Enable countdown timer
10. Set status to "Scheduled" or "Active"
11. Save

#### Targeting High Spenders
1. Create promotion with discount code
2. Set target audience: "High Spenders"
3. Set bonus amount or discount percentage
4. Set display location: "Dashboard"
5. The system will only show to users with $100+ spent

#### Welcome Bonus Campaign
1. Go to `/admin/settings/`
2. Set `new_user_welcome_bonus` to desired amount (e.g., 5.00)
3. The automated task will apply bonus to new users
4. Create a promotion banner to advertise the bonus

### 11. Frontend Integration

To display promotions on your frontend:

```javascript
// Fetch active promotions
fetch('/promotions/active/?location=homepage')
  .then(response => response.json())
  .then(data => {
    data.promotions.forEach(promo => {
      displayPromotion(promo);
      
      // Track view
      trackPromotionView(promo.promotion_id);
    });
  });

// Track view
function trackPromotionView(promotionId) {
  fetch('/promotions/track-view/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: `promotion_id=${promotionId}`
  });
}

// Track click
function trackPromotionClick(promotionId) {
  fetch('/promotions/track-click/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': getCookie('csrftoken')
    },
    body: `promotion_id=${promotionId}`
  });
}
```

### 12. Security Considerations

- All admin views require authentication and admin role
- Promotion tracking is rate-limited by max_views_per_user
- IP addresses are logged for fraud detection
- CSRF protection on all POST requests
- SQL injection protection through Django ORM

### 13. Database Migration

To apply the database changes:

```bash
python manage.py migrate panel
```

This will create the following tables:
- `panel_marketingpromotion`
- `panel_promotionview`
- `panel_promotionclick`
- `panel_promotionconversion`

### 14. Initial Settings Setup

Run this command to initialize the promotion settings:

```bash
python manage.py init_default_settings
```

### 15. Admin URLs Reference

| Function | URL | Method |
|----------|-----|--------|
| List Promotions | `/admin/promotions/` | GET |
| Create Promotion | `/admin/promotions/create/` | GET/POST |
| Edit Promotion | `/admin/promotions/<id>/edit/` | GET/POST |
| Delete Promotion | `/admin/promotions/<id>/delete/` | POST |
| Analytics | `/admin/promotions/<id>/analytics/` | GET |
| Track View | `/promotions/track-view/` | POST |
| Track Click | `/promotions/track-click/` | POST |
| Get Active | `/promotions/active/` | GET |

### 16. Best Practices

1. **Start with Draft**: Create promotions in draft status first to test
2. **Use Scheduling**: Schedule promotions to activate automatically
3. **Target Wisely**: Use audience targeting to avoid promotion fatigue
4. **Monitor Performance**: Check analytics regularly to optimize
5. **Limit Views**: Set max_views_per_user to avoid annoying users
6. **Test Mobile**: Upload separate mobile banners for better UX
7. **Clear CTAs**: Use compelling call-to-action text and links
8. **Time-Limited Offers**: Use countdown timers for urgency
9. **A/B Testing**: Create multiple promotions to test performance
10. **Follow Up**: Use analytics to inform future campaigns

### 17. Troubleshooting

#### Promotions Not Showing
- Check if promotion status is "Active"
- Verify start/end dates are correct
- Check target audience matches current user
- Ensure `marketing_enabled` setting is True
- Verify display location matches current page

#### Tracking Not Working
- Check CSRF token is included in requests
- Verify JavaScript is not blocked
- Check browser console for errors
- Ensure user is authenticated (for user-specific tracking)

#### Automated Tasks Not Running
- Verify Celery is running: `celery -A core worker -l info`
- Check Celery beat for scheduled tasks: `celery -A core beat -l info`
- Review logs for errors: `tail -f logs/celery.log`

### 18. Future Enhancements

Potential features for future development:
- Email template editor for promotional campaigns
- Multi-variant A/B testing
- Advanced segmentation rules
- Promotion templates library
- Social media sharing integration
- SMS notification support
- Promotion recommendation engine
- Dynamic pricing based on user behavior
- Gamification elements (spin wheel, scratch cards)
- Integration with external marketing platforms

## Conclusion

The Marketing Promotion Service provides a comprehensive solution for creating, managing, and tracking promotional campaigns in VinFlow. With powerful targeting, detailed analytics, and automated workflows, administrators can effectively boost user engagement and drive sales.

For questions or support, please contact the development team.

