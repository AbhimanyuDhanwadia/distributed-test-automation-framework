"""
Dummy test for verifying distributed test execution.
"""
import time


def test_success():
    """Simple test that sleeps for 1 second and passes."""
    time.sleep(1)
    assert True
