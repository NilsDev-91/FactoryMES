import zipfile
import os
import re

# Target File
FILE_PATH = "storage/3mf/5deb9307-6eff-44c3-85ff-96fc23181bdc.3mf"

def inspect_gcode():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found: {FILE_PATH}")
        return

    print(f"📂 Opening {FILE_PATH}...")
    
    try:
        with zipfile.ZipFile(FILE_PATH, 'r') as z:
            print(f"📂 Files in Archive:")
            for name in z.namelist():
                print(f" - {name}")

            # List files to find the GCode
            gcode_file = None
            for name in z.namelist():
                if name.startswith("Metadata/") and name.endswith(".gcode"):
                    gcode_file = name
                    print(f"✅ Found GCode: {name}")
                    if "plate_3" in name:
                        break # Prioritize the one we saw in logs
            
            if not gcode_file:
                print("❌ No GCode found in Metadata/")
                return

            print("\n----- INSPECTING 3D MODEL -----")
            target = "3D/3dmodel.model"
            if target in z.namelist():
                print(f"\n📂 Reading {target}...")
                with z.open(target) as f:
                    xml_content = f.read().decode('utf-8')
                    print(xml_content[:2000])
                    
                    # Search for color
                    import re
                    colors = re.findall(r'color="#[0-9A-Fa-f]{6,8}"', xml_content)
                    if colors:
                        print(f"\n🎨 Founds Colors: {colors}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_gcode()
