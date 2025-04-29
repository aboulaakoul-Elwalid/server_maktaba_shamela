@echo off
echo Testing Anonymous Chat (Non-Streaming)...
echo.

set API_BASE=http://localhost:8000
REM Escape double quotes inside the JSON for Windows curl
set MESSAGE_JSON_ESCAPED={\"content\": \"Tell me about the pillars of Islam\"}

echo Sending anonymous message: Tell me about the pillars of Islam
echo Request Body JSON: %MESSAGE_JSON_ESCAPED%
echo.

REM Use double quotes around the whole -d argument and escaped quotes inside
curl -X POST %API_BASE%/chat/messages ^
     -H "Content-Type: application/json" ^
     -d "%MESSAGE_JSON_ESCAPED%"

echo.
echo Anonymous test complete. Check output above and server logs.
echo Expected: AI response, sources, but conversation_id and message_id should be null or absent.
echo Expected Logs: Server logs should show 'Skipping history fetch', 'Skipping user message storage', 'Skipping AI message storage'.

pause REM Add pause to see output before window closes