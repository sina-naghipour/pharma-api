from django.core.management.base import BaseCommand
from django.utils.text import slugify
from products.models import Category, Manufacturer, Product
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Creates or updates demo pharmacy category hierarchy and sample products'

    def handle(self, *args, **options):
        self.stdout.write('Creating/updating demo data...')

        # Manufacturer
        manufacturer, _ = Manufacturer.objects.get_or_create(
            name='Demo Pharma Co.',
            defaults={'slug': 'demo-pharma', 'is_approved': True}
        )

        category_structure = {
            'دارو': ['قرص', 'شربت', 'کپسول', 'آمپول', 'پماد', 'قطره'],
            'آرایشی بهداشتی': ['شستشوی صورت', 'مرطوب کننده', 'ضد آفتاب', 'کرم دور چشم', 'ماسک صورت', 'ابرو و مژه', 'لاک و ناخن'],
            'مکمل غذایی': ['ویتامین ها', 'مواد معدنی', 'امگا 3', 'پروبیوتیک', 'گیاهی', 'کودکان'],
            'مکمل ورزشی': ['پروتئین وی', 'کراتین', 'BCAA', 'گینر', 'پیش از تمرین', 'ال کارنیتین'],
            'مادر و کودک': ['شیر خشک', 'پوشک', 'شامپو بچه', 'کرم پوشک', 'تب سنج', 'ویتامین کودک'],
            'تجهیزات پزشکی': ['فشارسنج', 'تب سنج', 'اکسیژن متر', 'دستگاه بخور', 'ماسک', 'گلوکومتر']
        }

        created_categories = {}
        for parent_name, children_names in category_structure.items():
            parent_slug = slugify(parent_name)
            parent, _ = Category.objects.get_or_create(
                slug=parent_slug,
                defaults={'name': parent_name, 'parent': None, 'is_active': True}
            )
            created_categories[parent_name] = parent
            for child_name in children_names:
                child_slug = slugify(f"{parent_name}-{child_name}")
                child, _ = Category.objects.get_or_create(
                    slug=child_slug,
                    defaults={'name': child_name, 'parent': parent, 'is_active': True}
                )
                created_categories[child_name] = child
                self.stdout.write(f"Category: {parent_name} -> {child_name}")

        sample_products = [
            ('آمپول سرم آنتی بیوتیک', 125000, 20, 'دارو', 'آمپول', 'محصول ضد عفونی کننده قوی'),
            ('قرص مسکن 500 میلی گرم', 85000, 50, 'دارو', 'قرص', 'تسکین درد و التهاب'),
            ('شربت سرفه گیاهی', 120000, 30, 'دارو', 'شربت', 'کاهش سرفه و خلط آور'),
            ('کرم ضد آفتاب SPF50', 250000, 45, 'آرایشی بهداشتی', 'ضد آفتاب', 'محافظت کامل در برابر UV'),
            ('ژل شستشوی صورت آلوئه ورا', 95000, 60, 'آرایشی بهداشتی', 'شستشوی صورت', 'پاک کننده ملایم'),
            ('سرم تقویت ابرو و مژه', 180000, 30, 'آرایشی بهداشتی', 'ابرو و مژه', 'حاوی بیوتین و پپتید'),
            ('لاک ناخن ژل‌ای', 65000, 90, 'آرایشی بهداشتی', 'لاک و ناخن', 'رنگ شاداب و ماندگاری بالا'),
            ('کپسول ویتامین D3 50000', 145000, 80, 'مکمل غذایی', 'ویتامین ها', 'تقویت استخوان و ایمنی'),
            ('قرص جوشان فروگلوبین', 210000, 40, 'مکمل غذایی', 'مواد معدنی', 'رفع کم خونی'),
            ('شربت پروبیوتیک کودکان', 175000, 25, 'مکمل غذایی', 'کودکان', 'بهبود هضم'),
            ('کپسول امگا ۳', 130000, 55, 'مکمل غذایی', 'امگا 3', 'مناسب قلب و مغز'),
            ('پروتئین وی ایزوله ۲ کیلو', 1250000, 20, 'مکمل ورزشی', 'پروتئین وی', 'عضله سازی'),
            ('کراتین مونوهیدرات ۳۰۰ گرم', 450000, 35, 'مکمل ورزشی', 'کراتین', 'افزایش قدرت'),
            ('BCAA 2:1:1 ۴۰۰ گرم', 680000, 25, 'مکمل ورزشی', 'BCAA', 'جلوگیری از تحلیل عضلات'),
            ('گینر ۳ کیلویی', 980000, 15, 'مکمل ورزشی', 'گینر', 'افزایش وزن'),
            ('پیش از تمرین قوی', 580000, 30, 'مکمل ورزشی', 'پیش از تمرین', 'افزایش انرژی'),
            ('ال کارنیتین مایع', 320000, 40, 'مکمل ورزشی', 'ال کارنیتین', 'چربی سوزی'),
            ('شیر خشک رشد ۱+', 650000, 50, 'مادر و کودک', 'شیر خشک', 'مناسب کودکان ۱ تا ۳ سال'),
            ('پوشک سایز ۳', 180000, 200, 'مادر و کودک', 'پوشک', 'نرم و ضد حساسیت'),
            ('شامپو بچه بدون اشک', 95000, 70, 'مادر و کودک', 'شامپو بچه', 'مواد طبیعی'),
            ('کرم ضد پوشک', 78000, 60, 'مادر و کودک', 'کرم پوشک', 'التیام التهاب'),
            ('تب سنج دیجیتال بچه', 120000, 40, 'مادر و کودک', 'تب سنج', 'دقت بالا'),
            ('ویتامین آ + د نوزادان', 145000, 30, 'مادر و کودک', 'ویتامین کودک', 'قطره خوراکی'),
            ('فشارسنج بازویی', 850000, 15, 'تجهیزات پزشکی', 'فشارسنج', 'دیجیتال با نمایشگر بزرگ'),
            ('تب سنج لیزری', 450000, 25, 'تجهیزات پزشکی', 'تب سنج', 'بدون تماس'),
            ('پالس‌اکسیمتر انگشتی', 280000, 30, 'تجهیزات پزشکی', 'اکسیژن متر', 'اندازه گیری اکسیژن خون'),
            ('دستگاه بخور سرد', 890000, 12, 'تجهیزات پزشکی', 'دستگاه بخور', 'تصفیه و مرطوب سازی'),
            ('ماسک سه لایه', 25000, 500, 'تجهیزات پزشکی', 'ماسک', 'بهداشتی با فیلتر'),
            ('گلوکومتر با نوار تست', 520000, 18, 'تجهیزات پزشکی', 'گلوکومتر', 'اندازه گیری قند خون')
        ]

        for name, price, stock, parent_cat, child_cat, desc in sample_products:
            try:
                category = Category.objects.get(name=child_cat, parent__name=parent_cat)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Category {parent_cat}->{child_cat} not found"))
                continue

            product_slug = slugify(name + str(random.randint(1000,9999)))
            product, created = Product.objects.get_or_create(
                name=name,
                manufacturer=manufacturer,
                defaults={
                    'slug': product_slug,
                    'sku': f'DEMO-{name[:3]}{random.randint(100,999)}',
                    'description': desc,
                    'price': Decimal(price),
                    'stock_quantity': stock,
                    'track_inventory': True,
                    'in_stock': stock > 0,
                    'is_active': True,
                    'is_featured': random.choice([True, False])
                }
            )
            if created:
                product.categories.add(category)
                self.stdout.write(f"Created product: {name}")
            else:
                # Update existing product's categories if needed
                if category not in product.categories.all():
                    product.categories.add(category)
                    self.stdout.write(f"Updated product {name}: added category {child_cat}")

        self.stdout.write(self.style.SUCCESS('Demo data created/updated successfully!'))