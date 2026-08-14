from pathlib import Path

BASE = Path("/root/rihan-platform")
settings_file = BASE / "src/rihan/settings.py"
content = settings_file.read_text(encoding="utf-8")

csrf_origins = """
CSRF_TRUSTED_ORIGINS = [
    'http://rihan360.ir',
    'https://rihan360.ir',
    'http://www.rihan360.ir',
    'https://www.rihan360.ir',
    'http://146.19.212.212',
    'http://146.19.212.212:8000',
]
"""
if "CSRF_TRUSTED_ORIGINS" not in content:
    content += csrf_origins
    settings_file.write_text(content, encoding="utf-8")
    print("✓ Configured CSRF_TRUSTED_ORIGINS for rihan360.ir")
