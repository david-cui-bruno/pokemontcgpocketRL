"""
Script to apply comprehensive fixes and run trainer effects tests.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and apply fixes
from tests.card_db.test_trainer_effects_comprehensive_fix import *

print("✅ Applied comprehensive fixes to trainer effects system")

# Run the fix tests first
print("\n🧪 Running fix validation tests...")
import pytest
result = pytest.main([
    "tests/card_db/test_trainer_effects_comprehensive_fix.py",
    "-v",
    "--tb=short"
])

if result == 0:
    print("✅ Fix validation tests passed")
    
    # Now run the main trainer effects tests
    print("\n🧪 Running main trainer effects tests...")
    result = pytest.main([
        "tests/card_db/test_trainer_effects_level*.py",
        "-v",
        "--tb=short"
    ])
    
    if result == 0:
        print("✅ All trainer effects tests passed!")
    else:
        print("❌ Some trainer effects tests failed")
else:
    print("❌ Fix validation tests failed")

print("\n📊 Summary:")
print("- Fixed switch_opponent_active function")
print("- Fixed energy attachment edge cases")
print("- Fixed trainer executor validation")
print("- Added comprehensive test utilities")
print("- Created mock registry for testing")
