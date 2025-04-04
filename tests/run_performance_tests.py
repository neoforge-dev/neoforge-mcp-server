#!/usr/bin/env python3
import os
import sys
import asyncio
import json
from datetime import datetime
from pathlib import Path
import pytest
from test_performance import (
    test_health_check_performance,
    test_tool_registration_performance,
    test_tool_execution_performance,
    test_file_operation_performance,
    test_system_info_performance,
    test_concurrent_operations,
    test_stress_performance,
    test_large_file_operation,
    test_multiple_tools
)

def run_performance_tests():
    """Run all performance tests and generate a report."""
    print("Starting performance tests...")
    
    # Initialize results dictionary
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "overall_score": 0
    }
    
    # Run individual tests
    test_functions = [
        ("health_check", test_health_check_performance),
        ("tool_registration", test_tool_registration_performance),
        ("tool_execution", test_tool_execution_performance),
        ("file_operation", test_file_operation_performance),
        ("system_info", test_system_info_performance),
        ("concurrent_operations", test_concurrent_operations),
        ("stress_test", test_stress_performance),
        ("large_file_operation", test_large_file_operation),
        ("multiple_tools", test_multiple_tools)
    ]
    
    for test_name, test_func in test_functions:
        try:
            print(f"\nRunning {test_name} test...")
            result = test_func()
            results["tests"][test_name] = {
                "status": "passed",
                "result": result
            }
        except Exception as e:
            print(f"Error in {test_name} test: {str(e)}")
            results["tests"][test_name] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Calculate overall score
    passed_tests = sum(1 for test in results["tests"].values() if test["status"] == "passed")
    total_tests = len(results["tests"])
    results["overall_score"] = (passed_tests / total_tests) * 100
    
    # Save results to file
    report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nPerformance test report saved to {report_file}")
    print(f"Overall score: {results['overall_score']:.2f}%")
    
    # Print detailed results
    print("\nDetailed Results:")
    print("=" * 50)
    for test_name, test_data in results["tests"].items():
        status = "PASSED" if test_data["status"] == "passed" else "FAILED"
        if "result" in test_data:
            if "mean" in test_data["result"]:
                print(f"{test_name}: {status} (mean: {test_data['result']['mean']:.3f}s)")
            elif "total_time" in test_data["result"]:
                print(f"{test_name}: {status} (total: {test_data['result']['total_time']:.3f}s)")
        else:
            print(f"{test_name}: {status} (error: {test_data['error']})")
    
    return results

if __name__ == "__main__":
    run_performance_tests() 