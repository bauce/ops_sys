"""测试环境开关：仅当 OPS_TEST_MODE=1 时启用免密登录。"""
import os


def is_test_mode() -> bool:
    return os.environ.get("OPS_TEST_MODE", "").strip().lower() in ("1", "true", "yes", "on")
