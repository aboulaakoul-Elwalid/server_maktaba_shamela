@REM @echo off
@REM echo Testing RAG Chat API - Single Conversation Test...
@REM echo.

@REM REM Set your base URL
@REM set API_BASE=https://server-maktaba-shamela.onrender.com

@REM REM 1. Register a new user
@REM echo 1. REGISTERING NEW USER...
@REM set EMAIL=test%RANDOM%@example.com
@REM set PASSWORD=TestPassword123!
@REM set NAME=Test User
@REM echo Email: %EMAIL%
@REM curl -s -X POST %API_BASE%/auth/register -H "Content-Type: application/json" -d "{\"email\": \"%EMAIL%\", \"password\": \"%PASSWORD%\", \"name\": \"%NAME%\"}" > register_response.json
@REM type register_response.json
@REM echo.

@REM REM 2. Login with registered user
@REM echo 2. LOGGING IN...
@REM curl -s -X POST %API_BASE%/auth/login -H "Content-Type: application/json" -d "{\"email\": \"%EMAIL%\", \"password\": \"%PASSWORD%\"}" > login_response.json
@REM type login_response.json

@REM REM Check if login was successful by looking for access_token in the response
@REM findstr /C:"\"access_token\"" login_response.json > nul
@REM if %errorlevel% neq 0 (
@REM     echo ERROR: Login failed or did not return an access token. Check login_response.json.
@REM     goto :eof
@REM )

@REM REM Extract token only if login was successful
@REM for /f "tokens=*" %%a in ('powershell -Command "(Get-Content login_response.json | ConvertFrom-Json).access_token"') do set AUTH_TOKEN=%%a
@REM echo Token: %AUTH_TOKEN%
@REM echo.

@REM REM 3. Create a conversation
@REM echo 3. CREATING CONVERSATION...
@REM curl -s -X POST %API_BASE%/chat/conversations -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" > conversation.json
@REM type conversation.json
@REM for /f "tokens=*" %%a in ('powershell -Command "(Get-Content conversation.json | ConvertFrom-Json).conversation_id"') do set CONV_ID=%%a
@REM echo Conversation ID: %CONV_ID%
@REM echo.

@REM REM 4. First Message: Ask about Islamic jurisprudence
@REM echo 4. SENDING FIRST MESSAGE...
@REM echo Request:
@REM echo {"content": "Tell me about Islamic jurisprudence", "conversation_id": "%CONV_ID%"}
@REM curl -s -X POST %API_BASE%/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" -d "{\"content\": \"Tell me about Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}" > message1_response.json
@REM echo Response:
@REM type message1_response.json
@REM echo.

@REM REM 5. Get conversation history after first message
@REM echo 5. GETTING CONVERSATION HISTORY (AFTER FIRST MESSAGE)...
@REM curl -s -X GET %API_BASE%/chat/conversations/%CONV_ID%/messages -H "Authorization: Bearer %AUTH_TOKEN%" > conversation_history1.json
@REM echo Conversation History:
@REM type conversation_history1.json
@REM echo.

@REM REM 6. Second Message: Follow-up on schools of thought
@REM echo 6. SENDING SECOND MESSAGE (FOLLOW-UP)...
@REM echo Request:
@REM echo {"content": "Explain the differences between the schools of thought in Islamic jurisprudence", "conversation_id": "%CONV_ID%"}
@REM curl -s -X POST %API_BASE%/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" -d "{\"content\": \"Explain the differences between the schools of thought in Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}" > message2_response.json
@REM echo Response:
@REM type message2_response.json
@REM echo.

@REM REM 7. Get conversation history after second message
@REM echo 7. GETTING CONVERSATION HISTORY (AFTER SECOND MESSAGE)...
@REM curl -s -X GET %API_BASE%/chat/conversations/%CONV_ID%/messages -H "Authorization: Bearer %AUTH_TOKEN%" > conversation_history2.json
@REM echo Conversation History:
@REM type conversation_history2.json
@REM echo.

@REM REM 8. Third Message: Ask about a specific scholar
@REM echo 8. SENDING THIRD MESSAGE (SPECIFIC SCHOLAR)...
@REM echo Request: 
@REM echo {"content": "Tell me about my last messages", "conversation_id": "%CONV_ID%"}
@REM curl -s -X POST %API_BASE%/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" -d "{\"content\": \"Tell me about Imam al-Shafi'i's contributions to Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}" > message3_response.json
@REM echo Response:
@REM type message3_response.json
@REM echo.

@REM REM 9. Get full conversation history after all messages
@REM echo 9. GETTING FULL CONVERSATION HISTORY...
@REM curl -s -X GET %API_BASE%/chat/conversations/%CONV_ID%/messages -H "Authorization: Bearer %AUTH_TOKEN%" > conversation_history_full.json
@REM echo Complete Conversation:
@REM type conversation_history_full.json
@REM echo.

@REM echo All tests completed for single conversation.

@echo off
echo Testing RAG Chat API - Streaming Conversation Test...
echo.

REM Set your base URL (Already set to Render)
set API_BASE=https://server-maktaba-shamela.onrender.com

REM 1. Register a new user (Keep as is)
echo 1. REGISTERING NEW USER...
set EMAIL=test%RANDOM%@example.com
set PASSWORD=TestPassword123!
set NAME=Test User
echo Email: %EMAIL%
curl -s -X POST %API_BASE%/auth/register -H "Content-Type: application/json" -d "{\"email\": \"%EMAIL%\", \"password\": \"%PASSWORD%\", \"name\": \"%NAME%\"}" > register_response.json
type register_response.json
echo.

REM 2. Login with registered user (Keep as is)
echo 2. LOGGING IN...
curl -s -X POST %API_BASE%/auth/login -H "Content-Type: application/json" -d "{\"email\": \"%EMAIL%\", \"password\": \"%PASSWORD%\"}" > login_response.json
type login_response.json
for /f "tokens=*" %%a in ('powershell -Command "(Get-Content login_response.json | ConvertFrom-Json).access_token"') do set AUTH_TOKEN=%%a
echo Token: %AUTH_TOKEN%
echo.

REM 3. Create a conversation (Keep as is)
echo 3. CREATING CONVERSATION...
curl -s -X POST %API_BASE%/chat/conversations -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" > conversation.json
type conversation.json
for /f "tokens=*" %%a in ('powershell -Command "(Get-Content conversation.json | ConvertFrom-Json).conversation_id"') do set CONV_ID=%%a
echo Conversation ID: %CONV_ID%
echo.

REM 4. First Message: Ask about Islamic jurisprudence (MODIFIED FOR STREAMING)
echo 4. SENDING FIRST MESSAGE (STREAMING)...
echo Request to: %API_BASE%/chat/messages/stream
echo {"content": "Tell me about Islamic jurisprudence", "conversation_id": "%CONV_ID%"}
echo --- Streaming Response Start ---
REM Use -N option with curl to disable buffering if available/helpful
curl -N -X POST %API_BASE%/chat/messages/stream ^
     -H "Content-Type: application/json" ^
     -H "Authorization: Bearer %AUTH_TOKEN%" ^
     -d "{\"content\": \"Tell me about Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}"
echo --- Streaming Response End ---
echo.

REM Clean up temporary files
del register_response.json login_response.json conversation.json 2>nul

echo Test complete. Check the streaming output above.
pause