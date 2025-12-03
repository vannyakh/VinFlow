# User Panel Marketing Promotions Handling

## Overview
This document explains how marketing promotions are handled and displayed in the user-facing panel of VinFlow.

## How Promotions Work in User Panel

### 1. Display Locations

Promotions can be configured to appear on different pages based on the **Display Location** setting:

- **Homepage**: Landing page (if exists)
- **User Dashboard**: Main dashboard page (`/panel/`)
- **Services Page**: Services listing page (`/services/`)
- **Checkout Page**: Add funds/payment pages (`/add-funds/`)
- **All Pages**: Shows on all configured pages

### 2. Target Audience Filtering

Promotions are automatically filtered based on user characteristics:

#### Available Target Audiences:
- **All Users**: Everyone sees the promotion
- **New Users**: Users registered within last 7 days
- **Active Users**: Users who have made at least one purchase
- **Inactive Users**: Users who haven't made any purchases
- **High Spenders**: Users who have spent $100 or more
- **Resellers**: Users with reseller accounts
- **Specific Users**: Manually selected users

#### How Filtering Works:
```python
# Example: Active Users
if promotion.target_audience == 'active_users':
    # Only show if user has made purchases
    if user.profile.total_spent > 0:
        show_promotion()
```

### 3. Promotion Display Methods

#### A. Dedicated Promotions Page
**URL**: `/promotions/`
- Full page listing all active promotions
- Card-based grid layout
- Shows all promotion details
- Countdown timers for time-limited offers
- Direct access from navigation menu

#### B. Dashboard Widget
**Location**: User Dashboard (`/panel/`)
- Shows up to 3 active promotions
- Compact card layout
- Quick preview with images
- Links to full promotions page
- Only shows promotions with `display_location='dashboard'` or `'all_pages'`

#### C. Page-Specific Banners
**Locations**: Services, Checkout pages
- Dynamic banner component
- Loads via JavaScript API
- Respects display location settings
- Automatic view tracking

### 4. Promotion Types & Display

#### Banner Promotions
- Full-width banner with image
- Appears at top of page
- Can include CTA button
- Best for homepage/services pages

#### Popup Promotions
- Modal overlay
- Appears after delay (configurable)
- Can be dismissed
- Best for important announcements

#### Notification Promotions
- In-app notification
- Appears in notification center
- Non-intrusive
- Best for updates/reminders

#### Flash Sale Promotions
- Time-limited offers
- Countdown timer
- High priority display
- Best for limited-time deals

#### Discount Campaign
- Shows discount percentage
- Displays coupon code
- Links to applicable services
- Best for sales events

#### Free Bonus
- Shows bonus amount
- Highlights free balance
- Encourages deposits
- Best for new user incentives

### 5. Automatic Tracking

#### View Tracking
- **When**: Promotion card enters viewport (50% visible)
- **How**: Uses Intersection Observer API
- **Data**: User, IP address, timestamp, user agent
- **Purpose**: Measure promotion visibility

#### Click Tracking
- **When**: User clicks CTA button
- **How**: JavaScript event listener
- **Data**: User, IP address, timestamp
- **Purpose**: Measure engagement

#### Conversion Tracking
- **When**: User completes action (order, deposit, signup)
- **How**: Backend integration
- **Data**: Conversion type, value, linked order/payment
- **Purpose**: Measure ROI

### 6. View Limits

#### Max Views Per User
- Configurable per promotion
- Prevents promotion fatigue
- Respects user experience
- `0` = unlimited views

**Example:**
```python
# Promotion with max 3 views per user
promotion.max_views_per_user = 3

# After 3 views, promotion won't show to that user
```

### 7. Promotion Priority

#### Display Priority
- Higher number = shown first
- Used for ordering multiple promotions
- Helps prioritize important offers

**Example:**
- Priority 10: Flash Sale (shown first)
- Priority 5: Regular Promotion
- Priority 1: Background Promotion

### 8. Countdown Timers

#### When Enabled
- Shows time remaining for time-limited offers
- Updates every minute
- Creates urgency
- Only for promotions with `show_countdown=True`

#### Display Format
```
2d 5h 30m remaining
```

### 9. Call-to-Action (CTA) Buttons

#### Configuration
- **Button Text**: Customizable (e.g., "Shop Now", "Get Started")
- **Button Link**: Can link to any page (e.g., `/services/`, `/add-funds/`)

#### Behavior
- Tracks clicks automatically
- Opens in same window (unless external link)
- Can link to:
  - Service pages
  - Checkout pages
  - Custom landing pages
  - External URLs

### 10. Bilingual Support

#### Language Detection
- Automatically detects user language preference
- Shows Khmer (`title_km`, `description_km`) if available
- Falls back to English if Khmer not available

#### Template Usage
```django
{% if is_khmer and promotion.title_km %}
    {{ promotion.title_km }}
{% else %}
    {{ promotion.title }}
{% endif %}
```

### 11. Promotion States

#### Active Promotions
- `is_active=True`
- `status='active'`
- `start_date <= now <= end_date`
- Visible to users

#### Scheduled Promotions
- `status='scheduled'`
- `start_date > now`
- Not yet visible
- Will auto-activate at start_date

#### Expired Promotions
- `end_date < now`
- `auto_expire=True`
- Automatically set to `status='completed'`
- No longer visible

### 12. Integration Points

#### Dashboard Integration
```django
<!-- In dashboard.html -->
{% if dashboard_promotions %}
    <!-- Show promotion widgets -->
{% endif %}
```

#### Services Page Integration
```django
<!-- In services.html -->
{% include 'panel/partials/promotion_banner.html' with location='services' %}
```

#### Checkout Page Integration
```django
<!-- In add_funds.html -->
{% include 'panel/partials/promotion_banner.html' with location='checkout' %}
```

### 13. JavaScript API

#### Fetch Active Promotions
```javascript
fetch('/promotions/active/?location=services')
    .then(response => response.json())
    .then(data => {
        // data.promotions contains array of active promotions
    });
```

#### Track View
```javascript
fetch('/promotions/track-view/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: `promotion_id=${promotionId}`
});
```

#### Track Click
```javascript
fetch('/promotions/track-click/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': getCookie('csrftoken')
    },
    body: `promotion_id=${promotionId}`
});
```

### 14. User Experience Features

#### Responsive Design
- Mobile-optimized layouts
- Touch-friendly buttons
- Adaptive images
- Responsive grid layouts

#### Performance
- Lazy loading of promotion images
- Intersection Observer for efficient view tracking
- Minimal JavaScript overhead
- Cached API responses

#### Accessibility
- Semantic HTML
- ARIA labels
- Keyboard navigation
- Screen reader support

### 15. Best Practices for Admins

#### Creating Effective Promotions

1. **Clear Messaging**
   - Use concise titles
   - Highlight key benefits
   - Include clear CTAs

2. **Visual Appeal**
   - Use high-quality banner images
   - Choose contrasting colors
   - Mobile-friendly designs

3. **Targeting**
   - Use appropriate audience targeting
   - Don't spam all users
   - Test with specific user groups

4. **Timing**
   - Set appropriate start/end dates
   - Use countdown timers for urgency
   - Schedule promotions in advance

5. **Testing**
   - Test on different devices
   - Verify tracking works
   - Check all display locations

### 16. Troubleshooting

#### Promotions Not Showing
- Check promotion status is "Active"
- Verify start/end dates are correct
- Confirm display location matches page
- Check target audience matches user
- Verify `marketing_enabled` setting is True

#### Tracking Not Working
- Check browser console for errors
- Verify CSRF token is included
- Check network tab for API calls
- Ensure user is authenticated

#### Images Not Loading
- Verify image files exist
- Check file permissions
- Confirm media URL is correct
- Check browser console for 404 errors

### 17. Analytics & Reporting

#### Available Metrics
- Total views per promotion
- Total clicks per promotion
- Click-through rate (CTR)
- Conversion rate
- Conversion value
- Daily breakdowns

#### Access Analytics
1. Go to Admin Panel → Promotions
2. Click on a promotion
3. Click "View Analytics"
4. See detailed performance metrics

### 18. Future Enhancements

Potential improvements:
- A/B testing support
- Advanced segmentation
- Email campaign integration
- SMS notifications
- Push notifications
- Social sharing
- Promotion templates
- Scheduled campaigns
- Multi-variant testing

## Summary

The user panel promotion system provides:
- ✅ Flexible display locations
- ✅ Smart audience targeting
- ✅ Automatic tracking
- ✅ Bilingual support
- ✅ Responsive design
- ✅ Performance optimized
- ✅ Easy integration
- ✅ Comprehensive analytics

For admin documentation, see: `MARKETING_PROMOTION_SERVICE.md`

