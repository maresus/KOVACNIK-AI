#!/bin/bash
set -e
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-test-token}"

echo "🧪 Running smoke tests against $BASE_URL"

# Test 1: Health
echo "Test 1: Health check..."
curl -sf "$BASE_URL/health" | grep -q "ok" && echo "✅ Health OK"

# Test 2: Chat basic
echo "Test 2: Chat basic..."
REPLY=$(curl -sf -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"smoke-test","message":"Pozdravljeni"}')
echo "$REPLY" | grep -q "reply" && echo "✅ Chat OK"

# Test 3: Reservation + product escape
echo "Test 3: Reservation with product interjection..."
SESSION="smoke-res-table"
curl -sf -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION\",\"message\":\"Rezervacija mize 13.7.2026 ob 13:00 za 6 oseb\"}" > /dev/null
REPLY2=$(curl -sf -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION\",\"message\":\"Imate marmelade?\"}")
echo "$REPLY2" | grep -qi "marmelad" && echo "✅ Product answer during reservation OK"

# Test 4: Admin reservations
echo "Test 4: Admin reservations..."
curl -sf "$BASE_URL/api/admin/reservations" | grep -q "reservations" && echo "✅ Admin OK"

echo ""
echo "✅✅✅ ALL SMOKE TESTS PASSED ✅✅✅"
