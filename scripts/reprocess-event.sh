#!/bin/bash
# Reprocess a specific event with updated entity extraction

if [ -z "$1" ]; then
    echo "Usage: ./reprocess-event.sh <event_id>"
    echo "Example: ./reprocess-event.sh 7570085e-3dbd-426d-b0d6-34adfbc66e22"
    exit 1
fi

EVENT_ID=$1
AI_CORE_URL="http://localhost:8000"

echo "Reprocessing event: $EVENT_ID"
echo ""

# Call the AI Core endpoint to process this specific event
curl -X POST "$AI_CORE_URL/process/event/$EVENT_ID" \
    -H "Content-Type: application/json" \
    | jq .

echo ""
echo "Done! Check the logs for extracted entities."
