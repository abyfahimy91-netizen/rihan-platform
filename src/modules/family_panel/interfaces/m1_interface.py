"""
M1 Interface - Real Connection to Catalog Module
Based on D-081: Remove Mock Mode
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional
from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Q, Sum, F

logger = logging.getLogger(__name__)


class M1Interface:
    """Real interface to Catalog module (M1)"""
    
    SAFE_MODE = True
    
    @classmethod
    def get_products_count(cls) -> int:
        """Count active products"""
        try:
            from src.modules.catalog.models import Product
            return Product.objects.filter(status='active').count()
        except Exception as e:
            logger.error(f"M1Interface.get_products_count error: {e}")
            return 0
    
    @classmethod
    def get_low_stock_products(cls, threshold: int = 5) -> List[Dict]:
        """Get products with low stock"""
        try:
            from src.modules.catalog.models import Product
            
            # Try to get inventory from related model
            products = []
            
            # Method 1: Try inventory_transactions
            try:
                low_stock = Product.objects.filter(
                    status='active'
                ).annotate(
                    total_stock=Sum('inventory_transactions__quantity_change')
                ).filter(
                    total_stock__lte=threshold
                )[:20]
                
                for p in low_stock:
                    products.append({
                        'id': str(p.id),
                        'name': p.name,
                        'slug': p.slug,
                        'stock': int(p.total_stock) if p.total_stock else 0,
                    })
                
                if products:
                    return products
            except Exception:
                pass
            
            # Method 2: Try inventory relation
            try:
                low_stock = Product.objects.filter(
                    status='active',
                    inventory__quantity__lte=threshold
                ).select_related('inventory')[:20]
                
                for p in low_stock:
                    products.append({
                        'id': str(p.id),
                        'name': p.name,
                        'slug': p.slug,
                        'stock': int(p.inventory.quantity) if hasattr(p, 'inventory') else 0,
                    })
                
                if products:
                    return products
            except Exception:
                pass
            
            # Method 3: Try direct stock field
            try:
                low_stock = Product.objects.filter(
                    status='active',
                    stock__lte=threshold
                )[:20]
                
                for p in low_stock:
                    products.append({
                        'id': str(p.id),
                        'name': p.name,
                        'slug': p.slug,
                        'stock': int(p.stock) if hasattr(p, 'stock') else 0,
                    })
            except Exception:
                pass
            
            return products
            
        except Exception as e:
            logger.error(f"M1Interface.get_low_stock_products error: {e}")
            return []
    
    @classmethod
    def get_categories(cls) -> List[Dict]:
        """Get categories with product counts"""
        try:
            from src.modules.catalog.models import Category
            
            categories = Category.objects.filter(
                is_active=True
            ).annotate(
                products_count=Count('products', filter=Q(products__status='active'))
            ).order_by('name')
            
            return [
                {
                    'id': str(c.id),
                    'name': c.name,
                    'slug': c.slug,
                    'products_count': c.products_count,
                }
                for c in categories
            ]
        except Exception as e:
            logger.error(f"M1Interface.get_categories error: {e}")
            return []
    
    @classmethod
    def get_recent_products(cls, days: int = 7) -> List[Dict]:
        """Get recently added products"""
        try:
            from src.modules.catalog.models import Product
            
            cutoff_date = timezone.now() - timedelta(days=days)
            products = Product.objects.filter(
                status='active',
                created_at__gte=cutoff_date
            ).order_by('-created_at')[:20]
            
            return [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'slug': p.slug,
                    'created_days_ago': (timezone.now() - p.created_at).days,
                    'base_price': str(p.base_price),
                }
                for p in products
            ]
        except Exception as e:
            logger.error(f"M1Interface.get_recent_products error: {e}")
            return []
    
    @classmethod
    def get_product_by_id(cls, product_id) -> Optional[Dict]:
        """Get a single product by ID"""
        try:
            from src.modules.catalog.models import Product
            p = Product.objects.get(id=product_id)
            return {
                'id': str(p.id),
                'name': p.name,
                'slug': p.slug,
                'base_price': str(p.base_price),
                'status': p.status,
                'unit': p.unit,
            }
        except Exception as e:
            logger.error(f"M1Interface.get_product_by_id error: {e}")
            return None
