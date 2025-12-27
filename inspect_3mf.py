
import zipfile
import sys
import os

def inspect_zip(file_path):
    print(f"Inspecting: {file_path}")
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            print("Contents:")
            for name in zip_ref.namelist():
                print(f" - {name}")
                
            # Check for Gcode
            gcode_files = [n for n in zip_ref.namelist() if n.endswith('.gcode')]
            if gcode_files:
                print(f"\nFOUND GCODE FILES: {gcode_files}")
            else:
                print("\nNO GCODE FILES FOUND inside ZIP.")
                
    except zipfile.BadZipFile:
        print("ERROR: Not a valid ZIP file.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_3mf.py <path_to_3mf>")
    else:
        inspect_zip(sys.argv[1])
