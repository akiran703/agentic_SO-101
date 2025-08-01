import unittest
import sys
import os
import time
from io import StringIO
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test modules to run
TEST_MODULES = ['tests.test_llm_providers','tests.test_robot_controller', 'tests.test_agent','tests.test_mcp_server','tests.test_config'
]

#unit testing class that logs the detaila
class DetailedTestResult(unittest.TestResult):
    
    def __init__(self):
        super().__init__()
        self.successes = []
        self.test_timings = {}
        self.start_time = None
        
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
        
    def stopTest(self, test):
        super().stopTest(test)
        if self.start_time:
            duration = time.time() - self.start_time
            self.test_timings[str(test)] = duration
            
    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)
        
    def addError(self, test, err):
        super().addError(test, err)
        
    def addFailure(self, test, err):
        super().addFailure(test, err)
        
    def addSkip(self, test, reason):
        super().addSkip(test, reason)


    #fucntion to check if all packages are avaliable 
def check_dependencies() -> bool:
        
        print("🔍 Checking dependencies...")
        
        required_packages = ['unittest','numpy','anthropic','google.genai','mcp','dotenv','PIL']
        
        missing_packages = []
        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package}")
            except ImportError:
                print(f"  ❌ {package} (missing)")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("Install them with: pip install -r requirements.txt")
            return False
        
        return True
#run tests based on a specific module 
def run_test_module(module_name: str) -> Tuple[DetailedTestResult, int]:
    
    print(f"\n{'='*60}")
    print(f"Running tests for: {module_name}")
    print('='*60)
    
    try:
        # Import the test module
        __import__(module_name)
        module = sys.modules[module_name]
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        
        # Run tests with custom result
        result = DetailedTestResult()
        suite.run(result)
        
        # Print results
        tests_run = result.testsRun
        successes = len(result.successes)
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        
        print(f"\nResults for {module_name}:")
        print(f"  Tests run: {tests_run}")
        print(f"  Successes: {successes}")
        print(f"  Failures: {failures}")
        print(f"  Errors: {errors}")
        print(f"  Skipped: {skipped}")

def main():
        """Main test runner function."""
        print("🧪 Robot MCP Project Test Suite")
        print("=" * 60)
        
        # Check dependencies first
        if not check_dependencies():
            print("\n❌ Cannot run tests due to missing dependencies.")
            sys.exit(1)
        
        # Set environment variables for testing
        os.environ['ANTHROPIC_API_KEY'] = 'test_key'
        os.environ['GEMINI_API_KEY'] = 'test_key'
        
        start_time = time.time()
        results = {}
        
        # Run each test module
        for module_name in TEST_MODULES:
            result, tests_run = run_test_module(module_name)
            results[module_name] = (result, tests_run)
        
        # Generate coverage report
        generate_coverage_report(results)
        
        # Print timing
        total_time = time.time() - start_time
        print(f"\n⏱️  Total execution time: {total_time:.2f}s")
        
        # Determine exit code
        has_failures = any(
            result and (result.failures or result.errors) 
            for result, _ in results.values()
        )
        
        if has_failures:
            print("\n❌ Some tests failed. Please review the output above.")
            sys.exit(1)
        else:
            print("\n✅ All tests completed successfully!")
            sys.exit(0)


    if __name__ == '__main__':
        main() 