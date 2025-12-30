import zipfile
import os
import re
import shutil

SOURCE_FILE = "storage/3mf/5deb9307-6eff-44c3-85ff-96fc23181bdc.3mf"
BACKUP_FILE = "storage/3mf/5deb9307-6eff-44c3-85ff-96fc23181bdc.3mf.bak"
TEMP_DIR = "storage/3mf/temp_patch"

def sanitize_3mf():
    if not os.path.exists(SOURCE_FILE):
        print(f"❌ Source file not found: {SOURCE_FILE}")
        return

    # 1. Backup
    print(f"💾 Backing up to {BACKUP_FILE}...")
    shutil.copy2(SOURCE_FILE, BACKUP_FILE)

    # 2. Extract
    print(f"📂 Extracting {SOURCE_FILE}...")
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    with zipfile.ZipFile(SOURCE_FILE, 'r') as z:
        z.extractall(TEMP_DIR)

    # 3. Modify GCode
    found_gcode = False
    for root, dirs, files in os.walk(TEMP_DIR):
        for file in files:
            if file.endswith(".gcode"):
                full_path = os.path.join(root, file)
                print(f"🔧 Patching GCode: {file}")
                
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # LOGIC: 
                # Find "T2" (or T1, T3...) and replace with "T0" ? 
                # OR remove them?
                # Usually best to normalize to T0 so standard mapping works.
                
                # Check for T2
                if "T2" in content:
                    print("   - Found T2 commands. Normalizing to T0...")
                    
                    # Regex to replace standalone "T2" or "Mxxx ... T2"
                    # Cases: "T2", "M109 S200 T2", "T2 ; comment"
                    
                    # Simple strings first
                    new_content = re.sub(r'\bT[1-9]\d*\b', 'T0', content)
                    
                    if content != new_content:
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print("   ✅ Patched to use T0.")
                        found_gcode = True
                    else:
                        print("   ⚠️ Regex didn't change anything (False positive?)")
    
    # 3b. Remove/Patch Metadata Configs
    print("🔧 Scanning Metadata for Configs...")
    files_to_remove = ["Metadata/filament_sequence.json", "Metadata/model_settings.config"]
    
    for root, dirs, files in os.walk(TEMP_DIR):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), TEMP_DIR).replace("\\", "/")
            
            # REMOVE explicit filament sequences
            if rel_path in files_to_remove:
                print(f"   🗑️ Removing {rel_path}...")
                os.remove(os.path.join(root, file))
                continue
            
            # PATCH slice_info.config (initial_extruder)
            if file.endswith(".config") or file.endswith(".json"):
                full_path = os.path.join(root, file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for "initial_extruder": 2 or "active_extruder": 2
                # Replace with 0
                original_content = content
                content = re.sub(r'"initial_extruder"\s*:\s*[1-9]\d*', '"initial_extruder": 0', content)
                content = re.sub(r'initial_extruder\s*=\s*[1-9]\d*', 'initial_extruder = 0', content)
                
                if content != original_content:
                    print(f"   ✨ Patched {file}: forced initial_extruder to 0")
                    with open(full_path, 'w', encoding='utf-8') as f:
                         f.write(content)

    if not found_gcode:
        print("⚠️ No GCode files found/patched.")
        # We proceed anyway if we removed configs? No, let's keep GCode restriction for now.
        pass

    # 4. Repackage
    print(f"📦 Repackaging to {SOURCE_FILE}...")
    
    # Create new zip
    with zipfile.ZipFile(SOURCE_FILE, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(TEMP_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, TEMP_DIR)
                z.write(file_path, arc_name)

    # Clean
    shutil.rmtree(TEMP_DIR)
    print("✨ Sanitization Complete. File is now Color-Agnostic (T0).")

if __name__ == "__main__":
    sanitize_3mf()
