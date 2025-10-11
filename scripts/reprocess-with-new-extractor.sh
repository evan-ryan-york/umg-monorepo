#!/bin/bash
# Reprocess your core identity event with the improved entity extractor

EVENT_ID="7570085e-3dbd-426d-b0d6-34adfbc66e22"
AI_CORE_URL="http://localhost:8000"

echo "======================================"
echo "Reprocessing Ryan York Core Identity Event"
echo "======================================"
echo ""
echo "Event ID: $EVENT_ID"
echo ""

# Step 1: Delete the old extracted data (prevents duplicates)
echo "Step 1: Deleting old extracted data..."
curl -s -X DELETE "$AI_CORE_URL/events/$EVENT_ID" | jq .
echo ""

# Step 2: Re-insert the event as pending_processing (manual approach)
echo "Step 2: You'll need to resubmit the text via Quick Capture OR manually reset status in DB"
echo ""
echo "To manually reset in Supabase:"
echo "UPDATE raw_events SET status = 'pending_processing' WHERE id = '$EVENT_ID';"
echo ""

# Step 3: Trigger processing
echo "Step 3: Triggering reprocessing..."
curl -s -X POST "$AI_CORE_URL/process/event/$EVENT_ID" | jq .
echo ""

echo "Done! Check the logs and /log page to see new extracted entities."
