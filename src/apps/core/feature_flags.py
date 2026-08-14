# M14: Feature Flags Engine (ADR-004)
import os
from typing import Dict

DEFAULT_FLAGS: Dict[str, bool] = {
    'FEATURE_CARD_TO_CARD_PAYMENT': True,
    'FEATURE_ONLINE_PAYMENT_GATEWAY': False,
    'FEATURE_SMS_OTP_LOGIN': True,
    'FEATURE_BACKUP_PASSWORD_LOGIN': True,
    'FEATURE_ORDER_TRACKING_PUBLIC': True,
    'FEATURE_PRODUCT_CONTENT_BLOCKS': True,
    'FEATURE_PRODUCT_BLOCK_JUNCTION': True,
    'FEATURE_SUPPLIER_PANEL': False,
    'FEATURE_CUSTOMER_REVIEWS': False,
    'FEATURE_LEAD_CAPTURE': False,
    'FEATURE_PLUGIN_HOOKS': True,
}

class FeatureFlags:
    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        env_val = os.environ.get(flag_name)
        if env_val is not None:
            return env_val.lower() in ('true', '1', 'yes')
        return DEFAULT_FLAGS.get(flag_name, False)

    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        return {k: cls.is_enabled(k) for k in DEFAULT_FLAGS.keys()}

    @classmethod
    def set_override(cls, flag_name: str, value: bool):
        DEFAULT_FLAGS[flag_name] = value
