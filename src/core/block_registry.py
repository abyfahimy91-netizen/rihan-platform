"""
M14: Block Registry (D-079)
سیستم ثبت بلوک‌های روایت‌گری محصول
"""
class BlockRegistry:
    _blocks = {}

    @classmethod
    def register(cls, block_type, block_class):
        cls._blocks[block_type] = block_class

    @classmethod
    def get_block_class(cls, block_type):
        return cls._blocks.get(block_type)
