from django.core.management.base import BaseCommand
from panel.models import SocialNetwork


class Command(BaseCommand):
    help = 'Seed social networks data'

    def handle(self, *args, **options):
        social_networks_data = [
            {
                'platform_code': 'ig',
                'name': 'Instagram',
                'name_km': 'អ៊ីនស្តាក្រាម',
                'description': 'Instagram followers, likes, views, and engagement services',
                'description_km': 'សេវាកម្ម Instagram អ្នកតាមដាន, ចូលចិត្ត, ទិដ្ឋភាព, និងការចូលរួម',
                'icon': 'fab fa-instagram',
                'color': '#E4405F',
                'status': 'active',
                'is_active': True,
                'is_featured': True,
                'display_order': 1,
                'website_url': 'https://www.instagram.com',
            },
            {
                'platform_code': 'fb',
                'name': 'Facebook',
                'name_km': 'ហ្វេសប៊ុក',
                'description': 'Facebook likes, followers, shares, and page promotion services',
                'description_km': 'សេវាកម្ម Facebook ចូលចិត្ត, អ្នកតាមដាន, ចែករំលែក, និងការផ្សព្វផ្សាយទំព័រ',
                'icon': 'fab fa-facebook',
                'color': '#1877F2',
                'status': 'active',
                'is_active': True,
                'is_featured': True,
                'display_order': 2,
                'website_url': 'https://www.facebook.com',
            },
            {
                'platform_code': 'tt',
                'name': 'TikTok',
                'name_km': 'ធីកថក',
                'description': 'TikTok followers, likes, views, and shares services',
                'description_km': 'សេវាកម្ម TikTok អ្នកតាមដាន, ចូលចិត្ត, ទិដ្ឋភាព, និងការចែករំលែក',
                'icon': 'fab fa-tiktok',
                'color': '#000000',
                'status': 'active',
                'is_active': True,
                'is_featured': True,
                'display_order': 3,
                'website_url': 'https://www.tiktok.com',
            },
            {
                'platform_code': 'yt',
                'name': 'YouTube',
                'name_km': 'យូធូប',
                'description': 'YouTube subscribers, views, likes, and watch time services',
                'description_km': 'សេវាកម្ម YouTube អ្នកជាវ, ទិដ្ឋភាព, ចូលចិត្ត, និងពេលវេលាមើល',
                'icon': 'fab fa-youtube',
                'color': '#FF0000',
                'status': 'active',
                'is_active': True,
                'is_featured': True,
                'display_order': 4,
                'website_url': 'https://www.youtube.com',
            },
            {
                'platform_code': 'tw',
                'name': 'Twitter/X',
                'name_km': 'ធ្វីតធឺរ/X',
                'description': 'Twitter/X followers, likes, retweets, and engagement services',
                'description_km': 'សេវាកម្ម Twitter/X អ្នកតាមដាន, ចូលចិត្ត, ចែករំលែកឡើងវិញ, និងការចូលរួម',
                'icon': 'fab fa-twitter',
                'color': '#1DA1F2',
                'status': 'active',
                'is_active': True,
                'is_featured': True,
                'display_order': 5,
                'website_url': 'https://twitter.com',
            },
            {
                'platform_code': 'sp',
                'name': 'Spotify',
                'name_km': 'ស្ពូទីហ្វៃ',
                'description': 'Spotify followers, plays, and playlist promotion services',
                'description_km': 'សេវាកម្ម Spotify អ្នកតាមដាន, ចាក់, និងការផ្សព្វផ្សាយបញ្ជីចាក់',
                'icon': 'fab fa-spotify',
                'color': '#1DB954',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 6,
                'website_url': 'https://www.spotify.com',
            },
            {
                'platform_code': 'li',
                'name': 'LinkedIn',
                'name_km': 'លីងខីន',
                'description': 'LinkedIn connections, followers, and profile views services',
                'description_km': 'សេវាកម្ម LinkedIn ការតភ្ជាប់, អ្នកតាមដាន, និងទិដ្ឋភាពប្រូហ្វាល',
                'icon': 'fab fa-linkedin',
                'color': '#0077B5',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 7,
                'website_url': 'https://www.linkedin.com',
            },
            {
                'platform_code': 'dc',
                'name': 'Discord',
                'name_km': 'ឌីសកូដ',
                'description': 'Discord members, server boosts, and engagement services',
                'description_km': 'សេវាកម្ម Discord សមាជិក, ការលើកទឹកចិត្តម៉ាស៊ីន, និងការចូលរួម',
                'icon': 'fab fa-discord',
                'color': '#5865F2',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 8,
                'website_url': 'https://discord.com',
            },
            {
                'platform_code': 'sc',
                'name': 'Snapchat',
                'name_km': 'ស្នេបឆែត',
                'description': 'Snapchat followers, views, and story views services',
                'description_km': 'សេវាកម្ម Snapchat អ្នកតាមដាន, ទិដ្ឋភាព, និងទិដ្ឋភាពរឿង',
                'icon': 'fab fa-snapchat',
                'color': '#FFFC00',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 9,
                'website_url': 'https://www.snapchat.com',
            },
            {
                'platform_code': 'twitch',
                'name': 'Twitch',
                'name_km': 'ធ្វីឆ',
                'description': 'Twitch followers, viewers, and channel promotion services',
                'description_km': 'សេវាកម្ម Twitch អ្នកតាមដាន, អ្នកមើល, និងការផ្សព្វផ្សាយឆានែល',
                'icon': 'fab fa-twitch',
                'color': '#9146FF',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 10,
                'website_url': 'https://www.twitch.tv',
            },
            {
                'platform_code': 'tg',
                'name': 'Telegram',
                'name_km': 'តេឡេក្រាម',
                'description': 'Telegram members, subscribers, and channel promotion services',
                'description_km': 'សេវាកម្ម Telegram សមាជិក, អ្នកជាវ, និងការផ្សព្វផ្សាយឆានែល',
                'icon': 'fab fa-telegram',
                'color': '#0088CC',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 11,
                'website_url': 'https://telegram.org',
            },
            {
                'platform_code': 'google',
                'name': 'Google',
                'name_km': 'ហ្គូហ្គល',
                'description': 'Google reviews, ratings, and business promotion services',
                'description_km': 'សេវាកម្ម Google ការពិនិត្យ, ការវាយតម្លៃ, និងការផ្សព្វផ្សាយអាជីវកម្ម',
                'icon': 'fab fa-google',
                'color': '#4285F4',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 12,
                'website_url': 'https://www.google.com',
            },
            {
                'platform_code': 'sh',
                'name': 'Shopee',
                'name_km': 'ស្ហូពី',
                'description': 'Shopee followers, reviews, and product promotion services',
                'description_km': 'សេវាកម្ម Shopee អ្នកតាមដាន, ការពិនិត្យ, និងការផ្សព្វផ្សាយផលិតផល',
                'icon': 'fas fa-shopping-cart',
                'color': '#EE4D2D',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 13,
                'website_url': 'https://shopee.com',
            },
            {
                'platform_code': 'web',
                'name': 'Website Traffic',
                'name_km': 'ចរាចរណ៍គេហទំព័រ',
                'description': 'Website traffic, visitors, and SEO promotion services',
                'description_km': 'សេវាកម្មចរាចរណ៍គេហទំព័រ, អ្នកទស្សនា, និងការផ្សព្វផ្សាយ SEO',
                'icon': 'fas fa-globe',
                'color': '#4CAF50',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 14,
                'website_url': '',
            },
            {
                'platform_code': 'review',
                'name': 'Reviews',
                'name_km': 'ការពិនិត្យ',
                'description': 'Review and rating services for various platforms',
                'description_km': 'សេវាកម្មការពិនិត្យនិងការវាយតម្លៃសម្រាប់វេទិកាផ្សេងៗ',
                'icon': 'fas fa-star',
                'color': '#FFA500',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 15,
                'website_url': '',
            },
            {
                'platform_code': 'other',
                'name': 'Others',
                'name_km': 'ផ្សេងៗ',
                'description': 'Other social media and platform services',
                'description_km': 'សេវាកម្មប្រព័ន្ធផ្សព្វផ្សាយសង្គមនិងវេទិកាផ្សេងៗ',
                'icon': 'fas fa-ellipsis-h',
                'color': '#9E9E9E',
                'status': 'active',
                'is_active': True,
                'is_featured': False,
                'display_order': 16,
                'website_url': '',
            },
        ]

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for data in social_networks_data:
            network, created = SocialNetwork.objects.get_or_create(
                platform_code=data['platform_code'],
                defaults=data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {network.name} ({network.platform_code})')
                )
            else:
                # Update existing network
                for key, value in data.items():
                    setattr(network, key, value)
                network.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ Updated: {network.name} ({network.platform_code})')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Seed completed! Created: {created_count}, Updated: {updated_count}, Total: {len(social_networks_data)}'
            )
        )

