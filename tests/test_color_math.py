import pytest
from app.utils.color_math import calculate_delta_e, hex_to_rgb, rgb_to_lab

def test_hex_to_rgb():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("ff0000") == (255, 0, 0)
    
    with pytest.raises(ValueError):
        hex_to_rgb("GGGGGG")
    with pytest.raises(ValueError):
        hex_to_rgb("FFF")

def test_delta_e_identity():
    # Identity test: Same color should have distance 0.0
    assert calculate_delta_e("#FFFFFF", "#FFFFFF") == 0.0
    assert calculate_delta_e("#000000", "#000000") == 0.0
    assert calculate_delta_e("#FF0000", "#FF0000") == 0.0

def test_delta_e_normalization():
    # Test that normalization (case, #) works
    res1 = calculate_delta_e("#FFFFFF", "#000000")
    res2 = calculate_delta_e("ffffff", "000000")
    assert res1 == res2

def test_delta_e_known_values():
    # White vs Black distance should be 100 in CIEDE2000 (roughly)
    # Actually, L goes from 0 to 100.
    dist = calculate_delta_e("#FFFFFF", "#000000")
    assert 99.0 < dist < 101.0

    # Test some common colors
    # Pure Red (#FF0000) vs Pure Green (#00FF00)
    # These are very different
    dist_rg = calculate_delta_e("#FF0000", "#00FF00")
    assert dist_rg > 50.0

    # Very similar colors
    # Light gray vs slightly lighter gray
    # Should be < 1.0 (unnoticeable)
    dist_sim = calculate_delta_e("#D3D3D3", "#D4D4D4")
    assert dist_sim < 1.0
