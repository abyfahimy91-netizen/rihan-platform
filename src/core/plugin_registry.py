"""
Plugin Registry - قلب معماری پلاگین‌محور ریهان

این فایل مسئولیت:
- ثبت ماژول‌ها
- ثبت بلوک‌ها
- مدیریت Feature Flags
- Hook System
را بر عهده دارد.
"""
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class PluginRegistry:
    """رجیستری مرکزی پلاگین‌ها"""
    
    _modules: Dict[str, Any] = {}
    _blocks: Dict[str, Any] = {}
    _hooks: Dict[str, List] = {}
    _feature_flags: Dict[str, bool] = {}
    
    @classmethod
    def register_module(cls, name: str, module: Any) -> None:
        """ثبت یک ماژول"""
        if name in cls._modules:
            logger.warning(f"ماژول {name} قبلاً ثبت شده است")
            return
        cls._modules[name] = module
        logger.info(f"✅ ماژول {name} ثبت شد")
    
    @classmethod
    def register_block(cls, name: str, block: Any) -> None:
        """ثبت یک بلوک"""
        if name in cls._blocks:
            logger.warning(f"بلوک {name} قبلاً ثبت شده است")
            return
        cls._blocks[name] = block
        logger.info(f"✅ بلوک {name} ثبت شد")
    
    @classmethod
    def get_module(cls, name: str) -> Any:
        """دریافت ماژول"""
        return cls._modules.get(name)
    
    @classmethod
    def get_block(cls, name: str) -> Any:
        """دریافت بلوک"""
        return cls._blocks.get(name)
    
    @classmethod
    def list_modules(cls) -> List[str]:
        """لیست همه ماژول‌های ثبت‌شده"""
        return list(cls._modules.keys())
    
    @classmethod
    def list_blocks(cls) -> List[str]:
        """لیست همه بلوک‌های ثبت‌شده"""
        return list(cls._blocks.keys())
    
    @classmethod
    def register_hook(cls, event: str, handler: callable) -> None:
        """ثبت یک hook"""
        if event not in cls._hooks:
            cls._hooks[event] = []
        cls._hooks[event].append(handler)
    
    @classmethod
    def trigger_hook(cls, event: str, *args, **kwargs) -> None:
        """فراخوانی همه handler های یک event"""
        for handler in cls._hooks.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"خطا در hook {event}: {e}")
    
    @classmethod
    def set_feature_flag(cls, name: str, value: bool) -> None:
        """تنظیم Feature Flag"""
        cls._feature_flags[name] = value
    
    @classmethod
    def is_feature_enabled(cls, name: str) -> bool:
        """بررسی وضعیت Feature Flag"""
        return cls._feature_flags.get(name, False)
