import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.core import PrinterStatusEnum
from app.models.printer import PrinterUpdate

def verify_schema():
    print("Verifying PrinterStatusEnum...")
    try:
        assert PrinterStatusEnum.AWAITING_CLEARANCE == "AWAITING_CLEARANCE"
        print("✅ AWAITING_CLEARANCE found in PrinterStatusEnum")
    except AttributeError:
        print("❌ AWAITING_CLEARANCE NOT found in PrinterStatusEnum")
        exit(1)

    print("\nVerifying PrinterUpdate model...")
    try:
        update_data = PrinterUpdate(current_status=PrinterStatusEnum.AWAITING_CLEARANCE)
        print(f"✅ PrinterUpdate instantiated successfully: {update_data}")
        assert update_data.current_status == PrinterStatusEnum.AWAITING_CLEARANCE
        print("✅ PrinterUpdate correctly holds new status")
    except Exception as e:
        print(f"❌ Failed to instantiate PrinterUpdate: {e}")
        exit(1)

if __name__ == "__main__":
    verify_schema()
