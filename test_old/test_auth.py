from appwrite.client import Client
from appwrite.services.users import Users
from appwrite.services.account import Account
import random

# Initialize Appwrite client
client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1')
client.set_project('67df69ef0039756850bd')
client.set_key('standard_020adda980312c55054c1ed7a59f03620f7051f547ae5313529a70a3cf36b5342c1cea07b229c19d586266472200fbc1bd466358def93a871f117eda24e2807eb42604168ee3be0739b036743f9c8dce5e5f09c2cbf74c31644c729595064cbd705ea242c17dd669263a37cd37bd3b12d78d1bd7a81e0fbc7dc8ccd8e0a0612e')

# Initialize services
users = Users(client)
account = Account(client)

# Test user credentials
test_email = f"testuser_{random.randint(1000,9999)}@example.com"
test_password = "StrongPassword123!"
test_name = f"Test User {random.randint(1000,9999)}"

print("\n--- 1) REGISTERING NEW USER ---")
print(f"Email: {test_email}")

# Create user
user = users.create(
    user_id='unique()',
    email=test_email,
    password=test_password,
    name=test_name
)
user_id = user['$id']
print(f"User created with ID: {user_id}")

# Create JWT
print("\n--- 2) CREATING JWT ---")
try:
    jwt_result = users.create_jwt(
        user_id=user_id
        # duration=0 # Temporarily removed for testing
    )
    jwt = jwt_result['jwt']
    print(f"JWT created: {jwt[:30]}...")

    # Test JWT by getting account info
    print("\n--- 3) FETCHING ACCOUNT WITH JWT ---")
    client.set_key('') # <-- Clear the API key
    client.set_jwt(jwt)  # Switch to JWT auth
    account_info = account.get()
    print(f"Account info retrieved for: {account_info['name']}")

except Exception as e:
    print(f"An error occurred: {e}")