"""
Inspect the contents of the source 3MF file to find the correct G-code path
"""
import zipfile
import os

# The master file that's being used
source_file = "storage/3mf/2feceedf-9dc7-4a65-8650-c76b99782f3a.3mf"

print(f"Inspecting: {source_file}")
print(f"Size: {os.path.getsize(source_file)} bytes")
print("\n=== Contents ===")

with zipfile.ZipFile(source_file, 'r') as z:
    for name in sorted(z.namelist()):
        info = z.getinfo(name)
        print(f"  {name} ({info.file_size} bytes)")
        
    # Check for gcode files specifically
    print("\n=== G-code Files ===")
    gcode_files = [n for n in z.namelist() if n.endswith('.gcode')]
    for g in gcode_files:
        print(f"  FOUND: {g}")
        
    if not gcode_files:
        print("  WARNING: No .gcode files found!")
        
    # Also check Metadata folder
    print("\n=== Metadata Folder ===")
    meta_files = [n for n in z.namelist() if n.startswith('Metadata/')]
    for m in meta_files:
        print(f"  {m}")
