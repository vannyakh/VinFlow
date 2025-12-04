from django.core.management.base import BaseCommand
from django.db.models import Q
from panel.models import ServiceCategory, SocialNetwork


class Command(BaseCommand):
    help = 'Update all ServiceCategory instances with SocialNetwork relationships by searching by name'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Automatically assign "Others" if no match found (non-interactive)',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip categories that already have a social_network assigned',
        )

    def handle(self, *args, **options):
        auto_mode = options['auto']
        skip_existing = options['skip_existing']
        
        # Get all categories
        categories = ServiceCategory.objects.all().order_by('name')
        
        if skip_existing:
            categories = categories.filter(social_network__isnull=True)
        
        if not categories.exists():
            self.stdout.write(
                self.style.WARNING('No categories found to update.')
            )
            return
        
        # Get or create "Others" social network as fallback
        try:
            others_network = SocialNetwork.objects.get(platform_code='other')
        except SocialNetwork.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('"Others" SocialNetwork not found. Please run seed_social_networks first.')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'\nFound {categories.count()} category(ies) to process.\n')
        )
        
        updated_count = 0
        skipped_count = 0
        not_found_count = 0
        
        for category in categories:
            # Show current category info
            current_network = category.social_network
            self.stdout.write(
                f'\n{"="*60}\n'
                f'Category: {category.name}'
            )
            
            if current_network:
                self.stdout.write(
                    self.style.WARNING(f'Current SocialNetwork: {current_network.name} ({current_network.platform_code})')
                )
                if skip_existing:
                    self.stdout.write(self.style.WARNING('Skipping (already has social_network)...'))
                    skipped_count += 1
                    continue
            
            # Search for matching social network
            if not auto_mode:
                search_name = input(f'\nEnter SocialNetwork name to search for (or press Enter to skip): ').strip()
                
                if not search_name:
                    self.stdout.write(self.style.WARNING('Skipped.'))
                    skipped_count += 1
                    continue
                
                # Search for matching social networks
                matching_networks = SocialNetwork.objects.filter(
                    Q(name__icontains=search_name) |
                    Q(name_km__icontains=search_name) |
                    Q(platform_code__icontains=search_name)
                ).distinct()
            else:
                # In auto mode, use smart matching
                # First, try to find if any social network name is contained in the category name
                matching_networks = None
                all_networks = SocialNetwork.objects.all()
                
                for network in all_networks:
                    # Check if social network name is in category name (case-insensitive)
                    if network.name.lower() in category.name.lower():
                        matching_networks = SocialNetwork.objects.filter(id=network.id)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Found "{network.name}" in category name "{category.name}"'
                            )
                        )
                        break
                    # Also check Khmer name if available
                    if network.name_km and network.name_km.lower() in category.name.lower():
                        matching_networks = SocialNetwork.objects.filter(id=network.id)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Found "{network.name_km}" in category name "{category.name}"'
                            )
                        )
                        break
                
                # If no match found, try searching with full category name
                if not matching_networks or not matching_networks.exists():
                    matching_networks = SocialNetwork.objects.filter(
                        Q(name__icontains=category.name) |
                        Q(name_km__icontains=category.name) |
                        Q(platform_code__icontains=category.name)
                    ).distinct()
            
            if matching_networks.exists():
                if matching_networks.count() == 1:
                    # Single match - use it
                    matched_network = matching_networks.first()
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Found match: {matched_network.name} ({matched_network.platform_code})')
                    )
                    category.social_network = matched_network
                    category.save()
                    updated_count += 1
                else:
                    # Multiple matches - show options
                    if auto_mode:
                        # In auto mode, use first match
                        matched_network = matching_networks.first()
                        self.stdout.write(
                            self.style.WARNING(
                                f'Multiple matches found. Using first: {matched_network.name} ({matched_network.platform_code})'
                            )
                        )
                        category.social_network = matched_network
                        category.save()
                        updated_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'\nFound {matching_networks.count()} matching SocialNetwork(s):')
                        )
                        for idx, network in enumerate(matching_networks, 1):
                            self.stdout.write(
                                f'  {idx}. {network.name} ({network.platform_code})'
                            )
                        
                        choice = input('\nEnter number to select (or press Enter to skip): ').strip()
                        
                        if choice.isdigit() and 1 <= int(choice) <= matching_networks.count():
                            matched_network = matching_networks[int(choice) - 1]
                            category.social_network = matched_network
                            category.save()
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✓ Assigned: {matched_network.name} ({matched_network.platform_code})'
                                )
                            )
                            updated_count += 1
                        else:
                            self.stdout.write(self.style.WARNING('Skipped.'))
                            skipped_count += 1
            else:
                # No match found - assign to "Others"
                self.stdout.write(
                    self.style.WARNING(
                        f'✗ No match found for "{category.name}". Assigning to "Others".'
                    )
                )
                category.social_network = others_network
                category.save()
                updated_count += 1
                not_found_count += 1
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n{"="*60}\n'
                f'Update completed!\n'
                f'  Updated: {updated_count}\n'
                f'  Skipped: {skipped_count}\n'
                f'  Assigned to "Others": {not_found_count}\n'
            )
        )

