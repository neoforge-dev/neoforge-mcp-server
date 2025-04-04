import subprocess
import time
import json
from datetime import datetime
import requests
from prometheus_client.parser import text_string_to_metric_families

def run_load_test(users: int = 10, spawn_rate: int = 1, duration: int = 60):
    """Run load test using Locust."""
    print(f"Starting load test with {users} users, spawn rate {spawn_rate} users/s, duration {duration}s")
    
    # Start monitoring server
    subprocess.Popen(["python", "-m", "server.utils.monitoring"])
    time.sleep(2)  # Wait for monitoring server to start
    
    # Start Locust
    locust_cmd = [
        "locust",
        "-f", "tests/load_test.py",
        "--headless",
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", f"{duration}s",
        "--host", "http://localhost:8000"
    ]
    
    subprocess.run(locust_cmd)
    
    # Collect metrics
    metrics = collect_metrics()
    
    # Save results
    save_results(metrics, users, spawn_rate, duration)

def collect_metrics():
    """Collect metrics from Prometheus."""
    response = requests.get("http://localhost:8000/metrics")
    metrics = {}
    
    for family in text_string_to_metric_families(response.text):
        for sample in family.samples:
            metric_name = sample.name
            if metric_name not in metrics:
                metrics[metric_name] = []
            metrics[metric_name].append({
                "labels": sample.labels,
                "value": sample.value
            })
    
    return metrics

def save_results(metrics: dict, users: int, spawn_rate: int, duration: int):
    """Save load test results to file."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "test_config": {
            "users": users,
            "spawn_rate": spawn_rate,
            "duration": duration
        },
        "metrics": metrics
    }
    
    filename = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Load test results saved to {filename}")

if __name__ == "__main__":
    # Run load test with different configurations
    configurations = [
        (10, 1, 60),    # 10 users, 1 user/s, 1 minute
        (50, 5, 120),   # 50 users, 5 users/s, 2 minutes
        (100, 10, 180)  # 100 users, 10 users/s, 3 minutes
    ]
    
    for users, spawn_rate, duration in configurations:
        run_load_test(users, spawn_rate, duration)
        time.sleep(5)  # Wait between tests 