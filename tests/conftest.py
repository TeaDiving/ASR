import pytest

from backend.xfyun_ai_correction import correction_context_memory


@pytest.fixture(autouse=True)
def clear_correction_context_memory():
    correction_context_memory.clear()
    yield
    correction_context_memory.clear()
