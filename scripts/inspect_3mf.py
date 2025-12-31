import zipfile
import re
import os

FILE_PATH = "storage/3mf/5deb9307-6eff-44c3-85ff-96fc23181bdc.3mf"

def inspect():
    if not os.path.exists(FILE_PATH):
        print(f"File not found: {FILE_PATH}")
        return

    print(f"Inspecting {FILE_PATH}...")
    
    with zipfile.ZipFile(FILE_PATH, 'r') as z:
        names = z.namelist()
        
        # Check for banned files
        banned = ["Metadata/filament_sequence.json", "Metadata/model_settings.config"]
        for b in banned:
            if b in names:
                print(f"❌ FOUND BANNED FILE: {b}")
            else:
                print(f"✅ Banned file absent: {b}")
        
        # Check GCode
        for name in names:
            if name.endswith(".gcode"):
                print(f"📄 Checking GCode: {name}")
                with z.open(name) as f:
                    content = f.read().decode('utf-8')
                    
                    # Find T commands
                    matches = re.findall(r'\bT([0-9]+)\b', content)
                    unique_t = set(matches)
                    print(f"   Found Tools: {unique_t}")
                    
                    if len(unique_t) == 0:
                        print("   ⚠️ No T commands found.")
                    elif len(unique_t) == 1 and "0" in unique_t:
                        print("   ✅ Only T0 is used. Good.")
                    else:
                        print(f"   ❌ MULTIPLE OR NON-ZERO TOOLS FOUND: {unique_t}")

                    # Check first few lines for M109/M190 to see which tool is primed
                    lines = content.split('\n')
                    for line in lines[:50]:
                        if "T" in line:
                           print(f"   Header Context: {line.strip()}")

        # Check Configs for initial_extruder
        for name in names:
            if name.endswith(".config") or name.endswith(".json"):
                with z.open(name) as f:
                    content = f.read().decode('utf-8')
                    if "initial_extruder" in content:
                        print(f"📄 Checking {name} for initial_extruder...")
                        matches = re.findall(r'"initial_extruder"\s*:\s*(\d+)', content)
                        if matches:
                            print(f"   Found initial_extruder: {matches}")
                        matches_eq = re.findall(r'initial_extruder\s*=\s*(\d+)', content)
                        if matches_eq:
                             print(f"   Found initial_extruder: {matches_eq}")

        # Check Model Colors
        for name in names:
            if name.endswith(".model"):
                print(f"🎨 Checking Model Color: {name}")
                with z.open(name) as f:
                    content = f.read().decode('utf-8')
                    if "C12E1F" in content: # Bambu Red
                         print("   ❌ FOUND RED COLOR (#C12E1F)")
                    elif "FFFFFF" in content or "ffffff" in content:
                         print("   ✅ Found White Color (#FFFFFF)")
                    else:
                         print("   ⚠️ No standard Red/White found (Custom color?)")
                         print(f"   Snippet: {content[:2000]}")

if __name__ == "__main__":
    inspect()
