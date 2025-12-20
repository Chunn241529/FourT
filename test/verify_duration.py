import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import LICENSE_DURATION_DAYS

def verify_duration():
    print("Verifying License Duration...")
    
    print(f"Configured Duration: {LICENSE_DURATION_DAYS} days")
    assert LICENSE_DURATION_DAYS == 30
    
    # Simulate expiration calculation
    now = datetime.now()
    expires_at = now + timedelta(days=LICENSE_DURATION_DAYS)
    
    diff = expires_at - now
    print(f"Time difference: {diff.days} days")
    
    assert diff.days == 30
    print("✅ Duration Logic Verified")

if __name__ == "__main__":
    try:
        verify_duration()
        print("\n🎉 Duration verification successful!")
    except AssertionError as e:
        print(f"\n❌ Verification Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
