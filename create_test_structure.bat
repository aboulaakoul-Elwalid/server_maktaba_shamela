@echo off
echo Creating test directory structure...

REM Ensure the main 'tests' directory exists
if not exist tests mkdir tests

REM Create main __init__.py and conftest.py placeholder
echo. > tests\__init__.py
echo REM Pytest fixtures go here > tests\conftest.py
echo REM Basic app tests go here > tests\test_main.py

REM Create api structure
if not exist tests\api mkdir tests\api
echo. > tests\api\__init__.py
echo REM Dependency tests go here > tests\api\test_dependencies.py

if not exist tests\api\endpoints mkdir tests\api\endpoints
echo. > tests\api\endpoints\__init__.py
echo REM Auth endpoint tests go here > tests\api\endpoints\test_auth.py
echo REM Chat endpoint tests go here > tests\api\endpoints\test_chat.py

REM Create core structure
if not exist tests\core mkdir tests\core
echo. > tests\core\__init__.py
echo REM Chat service tests go here > tests\core\test_chat_service.py
echo REM Context formatter tests go here > tests\core\test_context_formatter.py
echo REM LLM service tests go here > tests\core\test_llm_service.py
echo REM Storage tests go here > tests\core\test_storage.py
echo REM Streaming tests go here > tests\core\test_streaming.py

if not exist tests\core\retrieval mkdir tests\core\retrieval
echo. > tests\core\retrieval\__init__.py
echo REM Retriever factory tests go here > tests\core\retrieval\test_retriever_factory.py
echo REM Pinecone retriever tests go here > tests\core\retrieval\test_pinecone_retriever.py

REM Create models structure
if not exist tests\models mkdir tests\models
echo. > tests\models\__init__.py
echo REM Schema tests go here > tests\models\test_schemas.py

echo Test directory structure created successfully.
@echo on