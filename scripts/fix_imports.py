import os
import re

patterns = [
    (r"from app\.models\.core import (.*Printer.*)", r"from app.models import \1"),
    (r"from app\.models\.core import (.*Job.*)", r"from app.models import PrintJob as Job, \1"), # This might be tricky if Job is already there
    (r"from app\.models\.core import (.*PrinterStatusEnum.*)", r"from app.models import PrinterState as PrinterStatusEnum, \1"),
    (r"from app\.models\.core import (.*JobStatusEnum.*)", r"from app.models import JobStatus as JobStatusEnum, \1"),
]

# Better simpler replacements for exact matches first
simple_replacements = [
    ("from app.models.core import Printer, Job, PrinterStatusEnum, JobStatusEnum", "from app.models import Printer, PrintJob as Job, PrinterState as PrinterStatusEnum, JobStatus as JobStatusEnum"),
    ("from app.models.core import Printer, PrinterStatusEnum", "from app.models import Printer, PrinterState as PrinterStatusEnum"),
    ("from app.models.core import Job, JobStatusEnum", "from app.models import PrintJob as Job, JobStatus as JobStatusEnum"),
    ("from app.models.core import Printer", "from app.models import Printer"),
    ("from app.models.core import Job", "from app.models import PrintJob as Job"),
    ("from app.models.core import PrinterStatusEnum", "from app.models import PrinterState as PrinterStatusEnum"),
    ("from app.models.core import JobStatusEnum", "from app.models import JobStatus as JobStatusEnum"),
]

def fix_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original = content
    for old, new in simple_replacements:
        content = content.replace(old, new)
        
    # Clean up double imports if any (e.g. from app.models import ..., PrinterStatusEnum)
    # This is a bit naive but should work for most cases in this project
    content = content.replace("PrinterState as PrinterStatusEnum, PrinterState as PrinterStatusEnum", "PrinterState as PrinterStatusEnum")
    content = content.replace("JobStatus as JobStatusEnum, JobStatus as JobStatusEnum", "JobStatus as JobStatusEnum")
    
    if content != original:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False

for root, dirs, files in os.walk("app"):
    for file in files:
        if file.endswith(".py"):
            full_path = os.path.join(root, file)
            if fix_file(full_path):
                print(f"Fixed {full_path}")
