# 5 KRITIČNI LIVE TESTI ZA `/v2/chat`

Uporabi nov `session_id` za vsak test.

## TEST 1: Pozdrav + Info
```bash
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Živjo","session_id":"live-test-1"}' | jq .reply

curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Kje se nahajate?","session_id":"live-test-1"}' | jq .reply
```

## TEST 2: Room booking end-to-end
```bash
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Rad bi rezerviral sobo","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"22.7.2026","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"3","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"2 odrasla","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"ne","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"JULIJA","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Janez Novak","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"041123456","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"test@example.com","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"ne","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"brez posebnosti","session_id":"live-test-2"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"da","session_id":"live-test-2"}' | jq .reply
```

## TEST 3: Terminal guard interrupt
```bash
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Rad bi rezerviral sobo","session_id":"live-test-3"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"23.7.2026","session_id":"live-test-3"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"2","session_id":"live-test-3"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"2","session_id":"live-test-3"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"ne","session_id":"live-test-3"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"ANA","session_id":"live-test-3"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Koliko stane soba?","session_id":"live-test-3"}' | jq .reply
```

## TEST 4: Session isolation (A/B)
```bash
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Rad bi rezerviral sobo","session_id":"live-test-4a"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"24.7.2026","session_id":"live-test-4a"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Kakšna vina imate?","session_id":"live-test-4b"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"3 noči","session_id":"live-test-4a"}' | jq .reply
```

## TEST 5: Eksplicitna prekinitev
```bash
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"Rad bi rezerviral sobo","session_id":"live-test-5"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"25.7.2026","session_id":"live-test-5"}' | jq .reply
curl -s -X POST https://kovacnik-ai-production.up.railway.app/v2/chat -H "Content-Type: application/json" -d '{"message":"prekini","session_id":"live-test-5"}' | jq .reply
```
