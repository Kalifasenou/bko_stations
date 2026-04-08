#!/bin/bash
# ============================================================
# BKO Station - Deployment Verification Script
# Usage: ./verify_deployment.sh <backend_url> <frontend_url>
# Example: ./verify_deployment.sh https://bko-station-backend.onrender.com https://bko-station-frontend.onrender.com
# ============================================================

set -e

BACKEND_URL="${1:-http://localhost:8000}"
FRONTEND_URL="${2:-http://localhost:8080}"
PASS=0
FAIL=0
WARN=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; WARN=$((WARN+1)); }

echo "============================================================"
echo "  BKO Station - Deployment Verification"
echo "============================================================"
echo "Backend URL:  $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo "============================================================"
echo ""

# --------------------------------------------------------
# 1. Backend Health Check
# --------------------------------------------------------
echo "--- Backend Health ---"
HEALTH=$(curl -sf "${BACKEND_URL}/api/health/" 2>/dev/null || echo "")
if [ -n "$HEALTH" ]; then
    log_pass "Health endpoint reachable"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null && true
else
    log_fail "Health endpoint not reachable"
fi

# --------------------------------------------------------
# 2. API Stations Endpoint
# --------------------------------------------------------
echo ""
echo "--- Stations API ---"
STATIONS=$(curl -sf "${BACKEND_URL}/api/stations/" 2>/dev/null || echo "")
if [ -n "$STATIONS" ]; then
    COUNT=$(echo "$STATIONS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))" 2>/dev/null || echo "0")
    if [ "$COUNT" -gt 0 ]; then
        log_pass "Stations endpoint returned $COUNT stations"
    else
        log_warn "Stations endpoint returned 0 stations"
    fi
else
    log_fail "Stations endpoint not reachable"
fi

# --------------------------------------------------------
# 3. Auth Token Endpoint
# --------------------------------------------------------
echo ""
echo "--- Auth Token Endpoint ---"
TOKEN_RESP=$(curl -sf -X POST "${BACKEND_URL}/api/auth/token/" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}' 2>/dev/null || echo "")
if echo "$TOKEN_RESP" | grep -q "detail"; then
    log_pass "Token endpoint reachable (expected auth failure for test user)"
else
    log_warn "Token endpoint response unexpected"
fi

# --------------------------------------------------------
# 4. Statistics Endpoint
# --------------------------------------------------------
echo ""
echo "--- Statistics API ---"
STATS=$(curl -sf "${BACKEND_URL}/api/statistics/" 2>/dev/null || echo "")
if [ -n "$STATS" ]; then
    log_pass "Statistics endpoint reachable"
else
    log_fail "Statistics endpoint not reachable"
fi

# --------------------------------------------------------
# 5. Frontend Reachable
# --------------------------------------------------------
echo ""
echo "--- Frontend ---"
FRONT_HTML=$(curl -sf "${FRONTEND_URL}/" 2>/dev/null || echo "")
if echo "$FRONT_HTML" | grep -q "Bamako Gaz Tracker"; then
    log_pass "Frontend serving HTML correctly"
else
    log_fail "Frontend not serving expected content"
fi

# --------------------------------------------------------
# 6. Frontend Config
# --------------------------------------------------------
echo ""
echo "--- Frontend Config ---"
CONFIG_JS=$(curl -sf "${FRONTEND_URL}/config.js" 2>/dev/null || echo "")
if echo "$CONFIG_JS" | grep -q "API_BASE_URL"; then
    log_pass "Frontend config.js contains API_BASE_URL"
    API_URL=$(echo "$CONFIG_JS" | grep -o "https://[^']*" | head -1 || echo "not found")
    echo "  API URL: $API_URL"
else
    log_warn "Frontend config.js may not have API_BASE_URL"
fi

# --------------------------------------------------------
# 7. CORS Headers
# --------------------------------------------------------
echo ""
echo "--- CORS Headers ---"
CORS_HEADERS=$(curl -sI -X OPTIONS "${BACKEND_URL}/api/stations/" \
    -H "Origin: https://bko-station-frontend.onrender.com" \
    -H "Access-Control-Request-Method: GET" 2>/dev/null || echo "")
if echo "$CORS_HEADERS" | grep -qi "access-control-allow-origin"; then
    log_pass "CORS headers present"
else
    log_warn "CORS headers not detected (may be OK for same-origin)"
fi

# --------------------------------------------------------
# 8. Security Headers
# --------------------------------------------------------
echo ""
echo "--- Security Headers ---"
HEADERS=$(curl -sI "${BACKEND_URL}/api/health/" 2>/dev/null || echo "")
if echo "$HEADERS" | grep -qi "x-frame-options"; then
    log_pass "X-Frame-Options header present"
else
    log_warn "X-Frame-Options header missing"
fi
if echo "$HEADERS" | grep -qi "x-content-type-options"; then
    log_pass "X-Content-Type-Options header present"
else
    log_warn "X-Content-Type-Options header missing"
fi

# --------------------------------------------------------
# Summary
# --------------------------------------------------------
echo ""
echo "============================================================"
echo "  Verification Summary"
echo "============================================================"
echo -e "  ${GREEN}Passed: $PASS${NC}"
echo -e "  ${RED}Failed: $FAIL${NC}"
echo -e "  ${YELLOW}Warnings: $WARN${NC}"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}Some checks failed. Review the output above.${NC}"
    exit 1
else
    echo -e "${GREEN}All critical checks passed!${NC}"
    exit 0
fi
