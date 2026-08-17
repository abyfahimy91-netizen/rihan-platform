"""
Block Editor Views برای ماژول family_panel
منطبق بر US-055: سیستم بلوک‌محور
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ..decorators import require_family
from ..services import BlockEditorService
from ..interfaces.m14_interface import M14Interface


@require_GET
@require_family
def get_available_blocks(request):
    """لیست بلوک‌های موجود (از M14)"""
    blocks = M14Interface.get_available_blocks()
    
    return JsonResponse({
        'success': True,
        'blocks': blocks,
        'count': len(blocks),
    }, json_dumps_params={'ensure_ascii': False})


@require_GET
@require_family
def get_product_blocks(request, product_id):
    """دریافت بلوک‌های یک محصول"""
    blocks = BlockEditorService.get_blocks(product_id)
    
    return JsonResponse({
        'success': True,
        'product_id': product_id,
        'blocks': blocks,
        'count': len(blocks),
    }, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_family
def add_product_block(request, product_id):
    """
    افزودن بلوک به محصول.
    
    Body:
        {
            "block_type": "text",
            "data": {"content": "متن نمونه"},
            "order": 0
        }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    block_type = data.get('block_type')
    block_data = data.get('data', {})
    order = data.get('order')
    
    if not block_type:
        return JsonResponse({
            'success': False,
            'error': 'block_type الزامی است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    success, message, block = BlockEditorService.add_block(
        product_id=product_id,
        block_type=block_type,
        data=block_data,
        user=request.user,
        order=order,
    )
    
    if success:
        return JsonResponse({
            'success': True,
            'message': message,
            'block': block,
        }, json_dumps_params={'ensure_ascii': False})
    else:
        return JsonResponse({
            'success': False,
            'error': message,
        }, status=400, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_family
def update_product_block(request, product_id, block_id):
    """
    به‌روزرسانی بلوک.
    
    Body:
        {
            "data": {"content": "متن جدید"}
        }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    block_data = data.get('data', {})
    
    success, message = BlockEditorService.update_block(
        product_id=product_id,
        block_id=block_id,
        data=block_data,
        user=request.user,
    )
    
    status_code = 200 if success else 400
    return JsonResponse({
        'success': success,
        'message': message,
    }, status=status_code, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_family
def remove_product_block(request, product_id, block_id):
    """حذف بلوک"""
    success, message = BlockEditorService.remove_block(
        product_id=product_id,
        block_id=block_id,
        user=request.user,
    )
    
    status_code = 200 if success else 400
    return JsonResponse({
        'success': success,
        'message': message,
    }, status=status_code, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_family
def reorder_product_blocks(request, product_id):
    """
    تغییر ترتیب بلوک‌ها (drag & drop).
    
    Body:
        {
            "block_ids": ["id1", "id2", "id3"]
        }
    """
    try:
        data = json.loads(request.body)
        block_ids = data.get('block_ids', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    if not block_ids:
        return JsonResponse({
            'success': False,
            'error': 'block_ids الزامی است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    success, message = BlockEditorService.reorder_blocks(
        product_id=product_id,
        block_ids=block_ids,
        user=request.user,
    )
    
    status_code = 200 if success else 400
    return JsonResponse({
        'success': success,
        'message': message,
    }, status=status_code, json_dumps_params={'ensure_ascii': False})


@require_GET
@require_family
def preview_product(request, product_id):
    """پیش‌نمایش محصول (قبل از انتشار)"""
    preview = BlockEditorService.preview_product(product_id)
    
    return JsonResponse({
        'success': True,
        'preview': preview,
    }, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_family
def publish_product(request, product_id):
    """انتشار محصول"""
    success, message = BlockEditorService.publish_product(
        product_id=product_id,
        user=request.user,
    )
    
    status_code = 200 if success else 400
    return JsonResponse({
        'success': success,
        'message': message,
    }, status=status_code, json_dumps_params={'ensure_ascii': False})


@require_POST
@require_family
def save_draft(request, product_id):
    """
    ذخیره خودکار draft.
    
    Body:
        {
            "blocks": [...]
        }
    """
    try:
        data = json.loads(request.body)
        blocks = data.get('blocks', [])
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({
            'success': False,
            'error': 'JSON نامعتبر است',
        }, status=400, json_dumps_params={'ensure_ascii': False})
    
    success, message = BlockEditorService.save_draft(
        product_id=product_id,
        blocks=blocks,
        user=request.user,
    )
    
    return JsonResponse({
        'success': success,
        'message': message,
    }, json_dumps_params={'ensure_ascii': False})
