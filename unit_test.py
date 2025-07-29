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
