"""
Test executor module for running pytest tests.
"""
import subprocess
import time
from typing import Dict


def run_test(test_path: str) -> Dict[str, any]:
    """
    Execute a pytest test and capture the result.
    
    Args:
        test_path: Path to the test file or test case to execute
        
    Returns:
        Dictionary containing:
            - success (bool): Whether the test passed
            - output (str): Combined stdout and stderr
            - duration (float): Execution time in seconds
    """
    start_time = time.time()
    
    try:
        result = subprocess.run(
            ["pytest", test_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        duration = time.time() - start_time
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr,
            "duration": duration
        }
        
    except subprocess.TimeoutExpired as e:
        duration = time.time() - start_time
        
        return {
            "success": False,
            "output": f"Test execution timed out after 60 seconds\n{e.stdout or ''}\n{e.stderr or ''}",
            "duration": duration
        }
