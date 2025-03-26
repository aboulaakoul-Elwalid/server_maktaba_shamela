@echo off
echo Testing RAG Chat API - Single Conversation Test...
echo.

REM Set your base URL
set API_BASE=https://server-maktaba-shamela.onrender.com

REM 1. Register a new user
echo 1. REGISTERING NEW USER...
set EMAIL=test%RANDOM%@example.com
set PASSWORD=TestPassword123!
set NAME=Test User
echo Email: %EMAIL%
curl -s -X POST %API_BASE%/auth/register -H "Content-Type: application/json" -d "{\"email\": \"%EMAIL%\", \"password\": \"%PASSWORD%\", \"name\": \"%NAME%\"}" > register_response.json
type register_response.json
echo.

REM 2. Login with registered user
echo 2. LOGGING IN...
curl -s -X POST %API_BASE%/auth/login -H "Content-Type: application/json" -d "{\"email\": \"%EMAIL%\", \"password\": \"%PASSWORD%\"}" > login_response.json
type login_response.json
for /f "tokens=*" %%a in ('powershell -Command "(Get-Content login_response.json | ConvertFrom-Json).access_token"') do set AUTH_TOKEN=%%a
echo Token: %AUTH_TOKEN%
echo.

REM 3. Create a conversation
echo 3. CREATING CONVERSATION...
curl -s -X POST %API_BASE%/chat/conversations -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" > conversation.json
type conversation.json
for /f "tokens=*" %%a in ('powershell -Command "(Get-Content conversation.json | ConvertFrom-Json).conversation_id"') do set CONV_ID=%%a
echo Conversation ID: %CONV_ID%
echo.

REM 4. First Message: Ask about Islamic jurisprudence
echo 4. SENDING FIRST MESSAGE...
echo Request:
echo {"content": "Tell me about Islamic jurisprudence", "conversation_id": "%CONV_ID%"}
curl -s -X POST %API_BASE%/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" -d "{\"content\": \"Tell me about Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}" > message1_response.json
echo Response:
type message1_response.json
echo.

REM 5. Get conversation history after first message
echo 5. GETTING CONVERSATION HISTORY (AFTER FIRST MESSAGE)...
curl -s -X GET %API_BASE%/chat/conversations/%CONV_ID%/messages -H "Authorization: Bearer %AUTH_TOKEN%" > conversation_history1.json
echo Conversation History:
type conversation_history1.json
echo.

REM 6. Second Message: Follow-up on schools of thought
echo 6. SENDING SECOND MESSAGE (FOLLOW-UP)...
echo Request:
echo {"content": "Explain the differences between the schools of thought in Islamic jurisprudence", "conversation_id": "%CONV_ID%"}
curl -s -X POST %API_BASE%/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" -d "{\"content\": \"Explain the differences between the schools of thought in Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}" > message2_response.json
echo Response:
type message2_response.json
echo.

REM 7. Get conversation history after second message
echo 7. GETTING CONVERSATION HISTORY (AFTER SECOND MESSAGE)...
curl -s -X GET %API_BASE%/chat/conversations/%CONV_ID%/messages -H "Authorization: Bearer %AUTH_TOKEN%" > conversation_history2.json
echo Conversation History:
type conversation_history2.json
echo.

REM 8. Third Message: Ask about a specific scholar
echo 8. SENDING THIRD MESSAGE (SPECIFIC SCHOLAR)...
echo Request: 
echo {"content": "Tell me about Imam al-Shafi'i's contributions to Islamic jurisprudence", "conversation_id": "%CONV_ID%"}
curl -s -X POST %API_BASE%/chat/messages -H "Content-Type: application/json" -H "Authorization: Bearer %AUTH_TOKEN%" -d "{\"content\": \"Tell me about Imam al-Shafi'i's contributions to Islamic jurisprudence\", \"conversation_id\": \"%CONV_ID%\"}" > message3_response.json
echo Response:
type message3_response.json
echo.

REM 9. Get full conversation history after all messages
echo 9. GETTING FULL CONVERSATION HISTORY...
curl -s -X GET %API_BASE%/chat/conversations/%CONV_ID%/messages -H "Authorization: Bearer %AUTH_TOKEN%" > conversation_history_full.json
echo Complete Conversation:
type conversation_history_full.json
echo.

echo All tests completed for single conversation.