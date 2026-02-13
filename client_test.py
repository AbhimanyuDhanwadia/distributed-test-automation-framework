"""
Client test script to verify the DTAF cluster functionality.
Designed to run from within the Docker network.
"""
import requests
import redis
import json
import time
import sys


# Use controller service name when running in Docker, localhost otherwise
CONTROLLER_HOST = sys.argv[1] if len(sys.argv) > 1 else "controller"
REDIS_HOST = sys.argv[2] if len(sys.argv) > 2 else "redis"


def wait_for_workers():
    """Wait for workers to come online."""
    print("⏳ Waiting for workers to come online...")
    
    for i in range(30):
        try:
            response = requests.get(f"http://{CONTROLLER_HOST}:8000/metrics")
            if response.status_code == 200:
                metrics = response.json()
                worker_count = metrics.get("workers", 0)
                
                print(f"   Workers online: {worker_count}/3")
                
                if worker_count >= 3:
                    print("✅ Cluster Ready: 3 Workers Online.")
                    return True
        except requests.exceptions.RequestException as e:
            print(f"   Waiting for controller... ({i+1}/30)")
        
        time.sleep(2)
    
    print("❌ Timeout waiting for workers")
    return False


def submit_job():
    """Submit a test job to the controller."""
    print("\n🚀 Submitting job with 2 test tasks...")
    
    payload = {
        "test_paths": [
            "tests/dummy_test.py",
            "tests/dummy_test.py"
        ]
    }
    
    response = requests.post(f"http://{CONTROLLER_HOST}:8000/submit", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print(f"   Job ID: {result['job_id']}")
        print(f"   Tasks submitted: {result['count']}")
        print("🚀 Job Submitted.")
        return result['job_id']
    else:
        print(f"❌ Failed to submit job: {response.status_code}")
        return None


def check_results():
    """Check for test results in Redis."""
    print("\n🔍 Checking for results...")
    
    redis_client = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    
    for i in range(10):
        result_count = redis_client.llen("results")
        print(f"   Results received: {result_count}/2")
        
        if result_count >= 2:
            print("\n🎉 Success! Received 2 results from Redis.")
            print("\n📊 Results:")
            print("-" * 80)
            
            # Retrieve and display results
            for idx in range(result_count):
                result_json = redis_client.lindex("results", idx)
                result = json.loads(result_json)
                
                print(f"\nResult {idx + 1}:")
                print(f"  Task ID: {result['task_id']}")
                print(f"  Worker ID: {result['worker_id']}")
                print(f"  Status: {result['status']}")
                print(f"  Duration: {result['duration']:.2f}s")
                print(f"  Output Preview: {result['output'][:100]}...")
            
            print("-" * 80)
            return True
        
        time.sleep(1)
    
    print("❌ Timeout waiting for results")
    return False


def main():
    """Main test execution flow."""
    print("=" * 80)
    print("DTAF Cluster Verification Test")
    print(f"Controller: {CONTROLLER_HOST}:8000")
    print(f"Redis: {REDIS_HOST}:6379")
    print("=" * 80)
    
    # Step 1: Wait for workers
    if not wait_for_workers():
        return
    
    # Step 2: Submit job
    job_id = submit_job()
    if not job_id:
        return
    
    # Step 3: Check results
    if check_results():
        print("\n✅ All tests passed! DTAF cluster is working correctly.")
    else:
        print("\n❌ Test failed!")
    
    print("=" * 80)


if __name__ == "__main__":
    main()
