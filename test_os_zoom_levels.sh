#!/bin/bash
# Test OS API zoom levels to see which ones return valid tiles
# Testing a location in central England: around z/x/y coordinates

echo "Testing OS Leisure API zoom levels..."
echo "Using a sample tile location"
echo ""

for z in {0..20}; do
    # Calculate rough x/y for zoom level (this is approximate)
    # For EPSG:27700, we need to test valid tile coordinates
    x=$((2**z / 2))
    y=$((2**z / 2))
    
    url="https://api.os.uk/maps/raster/v1/zxy/Leisure_27700/${z}/${x}/${y}.png?key=${OS_API_KEY}"
    
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$http_code" = "200" ]; then
        echo "✓ Zoom level $z: Available (HTTP $http_code)"
    else
        echo "✗ Zoom level $z: Not available (HTTP $http_code)"
    fi
done
