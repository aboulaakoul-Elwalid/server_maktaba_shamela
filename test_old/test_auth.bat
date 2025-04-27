@echo off
setlocal EnableDelayedExpansion

REM ----------------------------------------------------------------
REM Test Appwrite Auth Flow (Register -> Create JWT -> Get Account)
REM ----------------------------------------------------------------

REM — Load Appwrite settings —
set "APPWRITE_ENDPOINT=https://cloud.appwrite.io/v1"
set "APPWRITE_PROJECT_ID=67df69ef0039756850bd"
set "APPWRITE_API_KEY=standard_020adda980312c55054c1ed7a59f03620f7051f547ae5313529a70a3cf36b5342c1cea07b229c19d586266472200fbc1bd466358def93a871f117eda24e2807eb42604168ee3be0739b036743f9c8dce5e5f09c2cbf74c31644c729595064cbd705ea242c17dd669263a37cd37bd3b12d78d1bd7a81e0fbc7dc8ccd8e0a0612e"

REM — Define Test User Credentials —
set "TEST_EMAIL=testuser_%RANDOM%@example.com"
set "TEST_PASSWORD=StrongPassword123!"
set "TEST_NAME=Test User %RANDOM%"

echo.
echo --- 1) REGISTERING NEW USER ---
echo Email: %TEST_EMAIL%
curl -s -X POST ^
  -H "Content-Type: application/json" ^
  -H "X-Appwrite-Project: %APPWRITE_PROJECT_ID%" ^
  -H "X-Appwrite-Key: %APPWRITE_API_KEY%" ^
  -d "{\"userId\":\"unique()\",\"email\":\"%TEST_EMAIL%\",\"password\":\"%TEST_PASSWORD%\",\"name\":\"%TEST_NAME%\"}" ^
  "%APPWRITE_ENDPOINT%/users" -o register.json

echo.
echo --- Registration Response ---
type register.json
echo --------------------------------

REM — Extract User ID using PowerShell —
for /f "tokens=* usebackq" %%i in (`powershell -Command "(Get-Content register.json | ConvertFrom-Json).'$id'"`) do (
    set "USER_ID=%%i"
)

echo Extracted USER_ID: %USER_ID%
if not defined USER_ID (
    echo ERROR: User ID not extracted. Aborting.
    goto :end
)

echo.
echo --- 2) CREATING JWT (Server-Side) ---
curl -s -X POST ^
  -H "Content-Type: application/json" ^
  -H "X-Appwrite-Project: %APPWRITE_PROJECT_ID%" ^
  -H "X-Appwrite-Key: %APPWRITE_API_KEY%" ^
  
  "%APPWRITE_ENDPOINT%/users/%USER_ID%/jwt" -o jwt.json

echo.
echo --- JWT Response ---
type jwt.json
echo --------------------------------

REM — Extract JWT using PowerShell —
for /f "tokens=* usebackq" %%j in (`powershell -Command "(Get-Content jwt.json | ConvertFrom-Json).jwt"`) do (
    set "APPWRITE_JWT=%%j"
)

echo Extracted JWT: %APPWRITE_JWT%
if not defined APPWRITE_JWT (
    echo ERROR: JWT not extracted. Aborting.
    goto :end
)

echo.
echo --- 3) FETCHING /account WITH JWT ---
curl -i ^
  -H "X-Appwrite-Project: %APPWRITE_PROJECT_ID%" ^
  -H "X-Appwrite-JWT: %APPWRITE_JWT%" ^
  "%APPWRITE_ENDPOINT%/account"
echo --------------------------------

:end
REM Clean up
del register.json jwt.json >nul 2>&1

pause