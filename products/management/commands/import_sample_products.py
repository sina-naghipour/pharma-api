import json
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Category, Manufacturer, Product


class Command(BaseCommand):
    help = 'Import a small sample of products (no CSV, no parsing)'

    def handle(self, *args, **options):
        # Define your sample products here – edit as needed
        sample_products = [
            # Sunscreen category
            {
                "name": "کرم ضد آفتاب فاقد چربی پوشش کرم پودر SPF30",
                "brand": "Ellaro",
                "original_price": 1492000,
                "discounted_price": 1417400,
                "discount_percent": 5,
                "category_slug": "sunscreen"
            },
            {
                "name": "کرم ضد آفتاب روشن کننده کرم پودری SPF50",
                "brand": "Sun Safe",
                "original_price": 485000,
                "discounted_price": 388000,
                "discount_percent": 20,
                "category_slug": "sunscreen"
            },
            # Supplement category
            {
                "name": "ول وومن اورجینال",
                "brand": "Vitabiotics",
                "original_price": 1023000,
                "discounted_price": 1023000,
                "discount_percent": 0,
                "category_slug": "supplement"
            },
            {
                "name": "اپتی وومن",
                "brand": "Golden Life",
                "original_price": 2322600,
                "discounted_price": 1625800,
                "discount_percent": 30,
                "category_slug": "supplement"
            },
            # Protein category
            {
                "name": "وی پروتئین 100 درصد 1800 گرمی",
                "brand": "Kalleh Pro",
                "original_price": 7300000,
                "discounted_price": 6716000,
                "discount_percent": 8,
                "category_slug": "protein"
            },
            {
                "name": "ایزو وی",
                "brand": "PNC",
                "original_price": 7095000,
                "discounted_price": 6598400,
                "discount_percent": 7,
                "category_slug": "protein"
            },
            # Hair care category
            {
                "name": "روفولیک مکس",
                "brand": "Abidi",
                "original_price": 351200,
                "discounted_price": 351200,
                "discount_percent": 0,
                "category_slug": "hair-care"
            },
            {
                "name": "کرم مرطوب کننده هیالورونیک اسید",
                "brand": "Folisense",
                "original_price": 1050000,
                "discounted_price": 840000,
                "discount_percent": 20,
                "category_slug": "hair-care"
            }
        ]

        # Ensure categories exist
        category_map = {}
        for item in sample_products:
            slug = item['category_slug']
            if slug not in category_map:
                cat, _ = Category.objects.get_or_create(
                    slug=slug,
                    defaults={'name': slug, 'is_active': True}
                )
                category_map[slug] = cat

        created_count = 0
        for item in sample_products:
            name = item['name']
            brand = item['brand']
            original_price = Decimal(item['original_price'])
            discounted_price = Decimal(item['discounted_price'])
            discount_percent = item['discount_percent']
            category = category_map[item['category_slug']]

            # Get or create manufacturer
            manufacturer, _ = Manufacturer.objects.get_or_create(
                name=brand,
                defaults={'slug': slugify(brand), 'is_approved': True}
            )

            # Create a unique slug
            product_slug = slugify(f'{name}-{brand}')[:280]
            base_slug = product_slug
            counter = 1
            while Product.objects.filter(slug=product_slug).exists():
                product_slug = f'{base_slug}-{counter}'
                counter += 1

            product, created = Product.objects.get_or_create(
                name=name,
                manufacturer=manufacturer,
                defaults={
                    'slug': product_slug,
                    'sku': f'SMP-{brand[:5]}{original_price}',
                    'price': discounted_price,
                    'compare_price': original_price if discount_percent > 0 else None,
                    'description': '',
                    'stock_quantity': 10,
                    'track_inventory': True,
                    'in_stock': True,
                    'is_active': True,
                }
            )
            if created:
                product.categories.add(category)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Added: {name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Already exists: {name}'))

        self.stdout.write(self.style.SUCCESS(f'Imported {created_count} products.'))