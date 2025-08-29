#!/bin/bash
# Test curl request to Gemini 2.5 Flash Image API
# This script tests what format the image data comes back in

API_KEY="AIzaSyBW518XAe55P8lmMDRwpYWPWUdQ0D_jMkQ"

# Use testbild.png if available, otherwise create a simple test image
TEST_IMAGE="testbild.png"

if [ ! -f "$TEST_IMAGE" ]; then
    echo "❌ Test image $TEST_IMAGE not found"
    echo "Please provide a test image or run this from the project directory"
    exit 1
fi

# Convert image to base64
IMAGE_BASE64=$(base64 -w 0 "$TEST_IMAGE")

echo "🚀 Testing Gemini 2.5 Flash Image API..."
echo "📸 Image size: $(wc -c < "$TEST_IMAGE") bytes"
echo "📝 Base64 size: ${#IMAGE_BASE64} chars"
echo "🔑 API Key: ${API_KEY:0:20}..."

# Create JSON payload
JSON_PAYLOAD=$(cat << EOF
{
  "contents": [
    {
      "parts": [
        {
          "text": "Perform light lip enhancement with 2.0ml hyaluronic acid. Add 35-45% volume to both upper and lower lips. IMPORTANT: Please edit and return the modified image showing the aesthetic treatment result. The output must be a visual image, not a text description."
        },
        {
          "inline_data": {
            "mime_type": "image/png",
            "data": "$IMAGE_BASE64"
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.1,
    "topP": 0.8,
    "maxOutputTokens": 8192
  }
}
EOF
)

echo "🌐 Making API request..."

# Make the API call and save response
RESPONSE=$(curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1alpha/models/gemini-2.5-flash-image-preview:generateContent?key=$API_KEY" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD")

echo "📋 Response saved to gemini_response.json"
echo "$RESPONSE" > gemini_response.json

# Analyze response structure
echo ""
echo "🔍 RESPONSE ANALYSIS:"
echo "==================="

# Check if response contains error
if echo "$RESPONSE" | jq -r '.error' 2>/dev/null | grep -q "null"; then
    echo "✅ No error in response"
else
    echo "❌ Error found:"
    echo "$RESPONSE" | jq -r '.error' 2>/dev/null
    exit 1
fi

# Check candidates
CANDIDATES_COUNT=$(echo "$RESPONSE" | jq -r '.candidates | length' 2>/dev/null)
echo "📊 Candidates count: $CANDIDATES_COUNT"

if [ "$CANDIDATES_COUNT" -gt 0 ]; then
    # Check parts in first candidate
    PARTS_COUNT=$(echo "$RESPONSE" | jq -r '.candidates[0].content.parts | length' 2>/dev/null)
    echo "🧩 Parts count: $PARTS_COUNT"
    
    # Analyze each part
    for i in $(seq 0 $((PARTS_COUNT-1))); do
        echo ""
        echo "📝 Part $i:"
        
        # Check for text
        TEXT_CONTENT=$(echo "$RESPONSE" | jq -r ".candidates[0].content.parts[$i].text" 2>/dev/null)
        if [ "$TEXT_CONTENT" != "null" ]; then
            echo "   📄 Text: ${TEXT_CONTENT:0:100}..."
        fi
        
        # Check for inline_data
        INLINE_DATA=$(echo "$RESPONSE" | jq -r ".candidates[0].content.parts[$i].inline_data" 2>/dev/null)
        if [ "$INLINE_DATA" != "null" ]; then
            echo "   🖼️  Has inline_data!"
            
            # Get MIME type
            MIME_TYPE=$(echo "$RESPONSE" | jq -r ".candidates[0].content.parts[$i].inline_data.mime_type" 2>/dev/null)
            echo "   📋 MIME type: $MIME_TYPE"
            
            # Get data (first 100 chars)
            DATA_CONTENT=$(echo "$RESPONSE" | jq -r ".candidates[0].content.parts[$i].inline_data.data" 2>/dev/null)
            DATA_LENGTH=${#DATA_CONTENT}
            echo "   📏 Data length: $DATA_LENGTH characters"
            echo "   🔤 First 50 chars: ${DATA_CONTENT:0:50}..."
            echo "   🔤 Last 50 chars: ...${DATA_CONTENT: -50}"
            
            # Try to detect if it's base64
            if echo "${DATA_CONTENT:0:100}" | grep -qE '^[A-Za-z0-9+/]*={0,2}$'; then
                echo "   ✅ Looks like Base64!"
                
                # Try to decode a small sample
                echo "   🧪 Testing Base64 decode..."
                SAMPLE_DECODE=$(echo "${DATA_CONTENT:0:100}" | base64 -d 2>/dev/null | hexdump -C | head -2)
                if [ $? -eq 0 ]; then
                    echo "   ✅ Base64 decoding works!"
                    echo "   🔍 Decoded sample (hex): $SAMPLE_DECODE"
                else
                    echo "   ❌ Base64 decoding failed!"
                fi
            else
                echo "   ❌ Does NOT look like Base64!"
                echo "   🔍 Hex dump of first 32 chars:"
                echo "${DATA_CONTENT:0:32}" | hexdump -C
            fi
            
            # Save the image data to file for testing
            echo "   💾 Saving image data to test_output.bin..."
            echo "$DATA_CONTENT" > test_image_data.txt
            
            # Try to decode as base64 and save as image
            if echo "$DATA_CONTENT" | base64 -d > test_output.png 2>/dev/null; then
                echo "   ✅ Base64 decoded image saved as test_output.png"
                if file test_output.png | grep -q "PNG\|JPEG\|image"; then
                    echo "   ✅ File is valid image format!"
                else
                    echo "   ❌ Decoded file is not a valid image"
                    file test_output.png
                fi
            else
                echo "   ❌ Base64 decoding failed"
            fi
        fi
    done
else
    echo "❌ No candidates in response"
fi

echo ""
echo "🏁 Test complete!"
echo "📁 Check gemini_response.json for full response"
echo "📁 Check test_output.png for decoded image (if successful)"