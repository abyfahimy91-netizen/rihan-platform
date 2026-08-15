(function($) {
    $(document).ready(function() {
        // Initialize sortable on content blocks
        var $blocksContainer = $('.inline-related');
        
        if ($blocksContainer.length > 0) {
            $blocksContainer.sortable({
                handle: '.content-block-drag-handle',
                placeholder: 'ui-sortable-placeholder',
                update: function(event, ui) {
                    updateBlockOrder();
                }
            });
        }
        
        // Add drag handle to each block
        $('.inline-related').each(function(index) {
            var $block = $(this);
            
            // Add drag handle if not exists
            if ($block.find('.content-block-drag-handle').length === 0) {
                var $header = $block.find('h3').first();
                if ($header.length > 0) {
                    $header.prepend('<span class="content-block-drag-handle">☰</span>');
                }
            }
            
            // Add block type badge
            var blockType = $block.find('select[name*="block_type"]').val();
            if (blockType && $block.find('.content-block-type').length === 0) {
                var $fieldset = $block.find('fieldset').first();
                if ($fieldset.length > 0) {
                    $fieldset.before('<div class="content-block-type">' + getBlockTypeLabel(blockType) + '</div>');
                }
            }
        });
        
        // Update block type badge on change
        $('select[name*="block_type"]').on('change', function() {
            var $block = $(this).closest('.inline-related');
            var blockType = $(this).val();
            var $badge = $block.find('.content-block-type');
            
            if ($badge.length > 0) {
                $badge.text(getBlockTypeLabel(blockType));
            }
        });
        
        // Function to update block order
        function updateBlockOrder() {
            var blockIds = [];
            
            $('.inline-related').each(function(index) {
                var $block = $(this);
                var blockId = $block.find('input[name*="-id"]').val();
                
                if (blockId) {
                    blockIds.push(blockId);
                }
                
                // Update sort_order field
                var $sortOrder = $block.find('input[name*="sort_order"]');
                if ($sortOrder.length > 0) {
                    $sortOrder.val(index);
                }
            });
            
            // Save to server (optional - can be done on form submit)
            if (blockIds.length > 0) {
                saveBlockOrder(blockIds);
            }
        }
        
        // Function to save block order to server
        function saveBlockOrder(blockIds) {
            $.ajax({
                url: '/admin/catalog/contentblock/reorder-blocks/',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ block_ids: blockIds }),
                success: function(response) {
                    if (response.success) {
                        console.log('Block order saved successfully');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Error saving block order:', error);
                }
            });
        }
        
        // Helper function to get block type label
        function getBlockTypeLabel(blockType) {
            var labels = {
                'text': 'متن آزاد',
                'heading': 'عنوان',
                'image': 'تک عکس',
                'gallery': 'گالری عکس',
                'video': 'ویدیو',
                'link': 'لینک',
                'quote': 'نقل قول',
                'table': 'جدول',
                'spacer': 'فاصله‌گذار',
                'cta': 'دکمه اقدام',
                'trust_badges': 'Trust Badges',
                'related_products': 'محصولات مرتبط'
            };
            
            return labels[blockType] || blockType;
        }
        
        // Preview block (optional)
        $('.preview-block-btn').on('click', function(e) {
            e.preventDefault();
            alert('پیش‌نمایش بلوک - در حال توسعه');
        });
    });
})(django.jQuery || jQuery);
