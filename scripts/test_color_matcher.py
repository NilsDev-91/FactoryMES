
from app.services.logic.color_matcher import color_matcher

def test_color_math():
    print("=== Testing ColorMatcher (CIEDE2000) ===")
    
    # 1. Identical Colors
    assert color_matcher.is_color_match("#FF0000", "#FF0000") == True
    print("[PASS] Identical colors match.")
    
    # 2. Perceptually Similar (Cool White vs Warm White)
    # White: #FFFFFF, Slight Grey: #F0F0F0
    match = color_matcher.is_color_match("#FFFFFF", "#F0F0F0", threshold=5.0)
    print(f"[*] Similar match (#FFFFFF vs #F0F0F0): {match}")
    
    # 3. Different Colors
    assert color_matcher.is_color_match("#FF0000", "#0000FF") == False
    print("[PASS] Red vs Blue does not match.")
    
    # 4. Bambu Lab 8-char Hex (RGBA)
    # Green #00FF00FF
    assert color_matcher.is_color_match("#00FF00FF", "#00FF00") == True
    print("[PASS] 8-char hex handled.")
    
    # 5. Null cases
    assert color_matcher.is_color_match(None, "#FFFFFF") == False
    assert color_matcher.is_color_match("#FFFFFF", None) == False
    print("[PASS] Null cases handled.")

if __name__ == "__main__":
    test_color_math()
