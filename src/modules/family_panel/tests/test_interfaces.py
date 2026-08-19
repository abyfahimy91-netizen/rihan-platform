"""
Test M3 Interfaces
Based on D-081: Remove Mock Mode
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from ..interfaces import M1Interface, M2Interface, M14Interface


class M1InterfaceTest(TestCase):
    """Test M1Interface"""
    
    def test_get_products_count_returns_int(self):
        """get_products_count should return int"""
        result = M1Interface.get_products_count()
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
    
    def test_get_categories_returns_list(self):
        """get_categories should return list"""
        result = M1Interface.get_categories()
        self.assertIsInstance(result, list)
    
    def test_get_low_stock_products_returns_list(self):
        """get_low_stock_products should return list"""
        result = M1Interface.get_low_stock_products(threshold=5)
        self.assertIsInstance(result, list)
    
    def test_get_recent_products_returns_list(self):
        """get_recent_products should return list"""
        result = M1Interface.get_recent_products(days=7)
        self.assertIsInstance(result, list)
    
    def test_get_product_by_id_invalid(self):
        """get_product_by_id with invalid ID should return None"""
        result = M1Interface.get_product_by_id('invalid-id')
        self.assertIsNone(result)


class M2InterfaceTest(TestCase):
    """Test M2Interface"""
    
    def test_get_orders_count_returns_int(self):
        """get_orders_count should return int"""
        result = M2Interface.get_orders_count()
        self.assertIsInstance(result, int)
        self.assertGreaterEqual(result, 0)
    
    def test_get_orders_count_with_status(self):
        """get_orders_count with status should work"""
        for status in ['pending', 'approved', 'shipped', 'delivered', None]:
            result = M2Interface.get_orders_count(status=status)
            self.assertIsInstance(result, int)
    
    def test_get_pending_orders_returns_list(self):
        """get_pending_orders should return list"""
        result = M2Interface.get_pending_orders()
        self.assertIsInstance(result, list)
    
    def test_get_revenue_returns_int(self):
        """get_revenue should return int"""
        for period in ['today', 'week', 'month']:
            result = M2Interface.get_revenue(period=period)
            self.assertIsInstance(result, int)
            self.assertGreaterEqual(result, 0)
    
    def test_get_sales_chart_data_returns_list(self):
        """get_sales_chart_data should return list"""
        result = M2Interface.get_sales_chart_data(days=7)
        self.assertIsInstance(result, list)
        if result:
            self.assertIn('date', result[0])
            self.assertIn('revenue', result[0])
            self.assertIn('orders_count', result[0])
    
    def test_get_orders_without_receipt_returns_list(self):
        """get_orders_without_receipt should return list"""
        result = M2Interface.get_orders_without_receipt()
        self.assertIsInstance(result, list)


class M14InterfaceTest(TestCase):
    """Test M14Interface"""
    
    def test_get_available_blocks_returns_list(self):
        """get_available_blocks should return list"""
        blocks = M14Interface.get_available_blocks()
        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)
    
    def test_validate_block_data(self):
        """validate_block_data should return tuple"""
        is_valid, msg = M14Interface.validate_block_data('text', {'content': 'test'})
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(msg, str)
    
    def test_render_block(self):
        """render_block should return string"""
        html = M14Interface.render_block('text', {'content': 'test'})
        self.assertIsInstance(html, str)
    
    def test_get_block_types_returns_list(self):
        """get_block_types should return list"""
        types = M14Interface.get_block_types()
        self.assertIsInstance(types, list)
        self.assertGreater(len(types), 0)
