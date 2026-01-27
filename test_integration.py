#!/usr/bin/env python3
"""Integration tests for tile server"""

import os
import sys
import time
import requests
from PIL import Image
from io import BytesIO

MAPPROXY_URL = os.getenv("MAPPROXY_URL", "http://localhost:8080")
MAX_RETRIES = 30
RETRY_DELAY = 2


def wait_for_service():
    print(f"Waiting for MapProxy service at {MAPPROXY_URL}...")
    for i in range(MAX_RETRIES):
        try:
            response = requests.get(f"{MAPPROXY_URL}/", timeout=5)
            if response.status_code == 200:
                print("✓ Service is ready")
                return True
        except requests.RequestException:
            pass
        time.sleep(RETRY_DELAY)
    print(f"✗ Service failed to start after {MAX_RETRIES * RETRY_DELAY} seconds")
    return False


def assert_tile_response(response):
    if response.status_code != 200:
        print(f"Error response ({response.status_code}):")
        print(response.text[:500])
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    img = Image.open(BytesIO(response.content))
    # check is 256x256 PNG
    assert img.size == (256, 256), f"Expected 256x256 tile, got {img.size}"
    assert img.format == "PNG", f"Expected PNG format, got {img.format}"
    # Check not entirely transparent
    if img.mode == "RGBA":
        alpha = img.split()[-1]
        if not alpha.getextrema()[1]:  # max alpha value
            raise AssertionError("Tile is entirely transparent")


def test_demo_interface():
    print("\nTesting demo interface...")
    response = requests.get(f"{MAPPROXY_URL}/demo/")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "MapProxy" in response.text, "Demo page doesn't contain 'MapProxy'"
    print("✓ Demo interface accessible")


def test_wmts_capabilities():
    print("\nTesting WMTS GetCapabilities...")
    response = requests.get(f"{MAPPROXY_URL}/wmts/1.0.0/WMTSCapabilities.xml")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert (
        "WMTSCapabilities" in response.text
    ), "Response doesn't contain WMTSCapabilities"
    assert "os_leisure" in response.text, "Layer 'os_leisure' not found in capabilities"
    print("✓ WMTS capabilities valid")


def test_os_leisure_reprojected_tile_wmts():
    print("\nTesting WMTS tile retrieval...")
    response = requests.get(f"{MAPPROXY_URL}/wmts/os_leisure/3857/8/127/82.png")

    # Verify it's a valid image
    assert_tile_response(response)
    print(f"✓ WMTS tile retrieved successfully")


def test_os_leisure_reprojected_tile_slippy():
    print("\nTesting slippy tile retrieval...")
    response = requests.get(f"{MAPPROXY_URL}/tiles/os_leisure/3857/10/502/303.png")

    # Verify it's a valid image
    assert_tile_response(response)
    print(f"✓ TMS tile retrieved successfully")


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("plantopo-tiles integration tests")
    print("=" * 60)

    if not wait_for_service():
        sys.exit(1)

    tests = [
        test_demo_interface,
        test_wmts_capabilities,
        test_os_leisure_reprojected_tile_wmts,
        test_os_leisure_reprojected_tile_slippy,
    ]

    failed = 0
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"✓ All {len(tests)} tests passed!")
        print("=" * 60)
        sys.exit(0)
    else:
        print(f"✗ {failed}/{len(tests)} tests failed")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
