@echo off
echo Testing Anonymous Chat (Non-Streaming)...
echo.

set API_BASE=http://localhost:8000

REM First message
set MESSAGE_JSON_ESCAPED={\"content\": \"Tell me about the pillars of Islam\"}

echo Sending anonymous message: Tell me about the pillars of Islam
echo Request Body JSON: %MESSAGE_JSON_ESCAPED%
echo.

curl -X POST %API_BASE%/chat/messages ^
     -H "Content-Type: application/json" ^
     -d "%MESSAGE_JSON_ESCAPED%"

echo.
echo First anonymous test complete. Check output above and server logs.
echo Expected: AI response, sources, but conversation_id and message_id should be null or absent.
echo Expected Logs: Server logs should show 'Skipping history fetch', 'Skipping user message storage', 'Skipping AI message storage'.
echo.

REM Second message (first follow-up)
set MESSAGE_JSON_ESCAPED={\"content\": \"what was my firt message.\"}

echo Sending follow-up anonymous message: List them briefly.
echo Request Body JSON: %MESSAGE_JSON_ESCAPED%
echo.

curl -X POST %API_BASE%/chat/messages ^
     -H "Content-Type: application/json" ^
     -d "%MESSAGE_JSON_ESCAPED%"

echo.
echo Second anonymous test complete. Check output above and server logs.
echo.

REM Third message (second follow-up)
set MESSAGE_JSON_ESCAPED={\"content\": \"Which one is the most important?\"}

echo Sending follow-up anonymous message: Which one is the most important?
echo Request Body JSON: %MESSAGE_JSON_ESCAPED%
echo.

curl -X POST %API_BASE%/chat/messages ^
     -H "Content-Type: application/json" ^
     -d "%MESSAGE_JSON_ESCAPED%"

echo.
echo Third anonymous test complete. Check output above and server logs.
echo Expected: Each response should be independent, with no conversation_id or message_id.
echo Expected Logs: Server logs should show 'Skipping history fetch', 'Skipping user message storage', 'Skipping AI message storage' for each request.

pause REM Add pause to see output before window closes