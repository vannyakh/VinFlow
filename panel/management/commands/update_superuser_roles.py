"""
Management command to update superuser profiles to have admin role.
Run this command to fix existing superusers who don't have admin role in their profile.

Usage:
    python manage.py update_superuser_roles
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from panel.models import UserProfile


class Command(BaseCommand):
    help = 'Update all superusers to have admin role in their profile'

    def handle(self, *args, **options):
        superusers = User.objects.filter(is_superuser=True)
        updated_count = 0
        created_count = 0
        
        for user in superusers:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'admin'}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created profile with admin role for superuser: {user.username}'
                    )
                )
            elif profile.role != 'admin':
                profile.role = 'admin'
                profile.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated profile role to admin for superuser: {user.username}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCompleted! Created {created_count} profiles, updated {updated_count} profiles.'
            )
        )

