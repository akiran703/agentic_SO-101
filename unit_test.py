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
        
        required_packages = [
            'unittest',
            'numpy',
            'anthropic',
            'google.genai',
            'mcp',
            'dotenv',
            'PIL'
        ]
        
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