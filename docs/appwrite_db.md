Skip to content
appwrite

Search in docs
Getting started
Overview
Quick start
APIs
Account
Users
Teams
Databases
Storage
Functions
Messaging
Localization
Avatars

Databases
SERVER
Platform
Version
The Databases service allows you to create structured collections of documents, query and filter lists of documents, and manage an advanced set of read and write access permissions.

All data returned by the Databases service are represented as structured JSON documents.

The Databases service can contain multiple databases, each database can contain multiple collections. A collection is a group of similarly structured documents. The accepted structure of documents is defined by collection attributes. The collection attributes help you ensure all your user-submitted data is validated and stored according to the collection structure.

Using Appwrite permissions architecture, you can assign read or write access to each collection or document in your project for either a specific user, team, user role, or even grant it with public access (any). You can learn more about how Appwrite handles permissions and access control.

Base URL

https://cloud.appwrite.io/v1
List databases
Get a list of all databases from the current Appwrite project. You can use the search parameter to filter your results.

Request
queries
array
Array of query strings generated using the Query class provided by the SDK. Learn more about queries. Maximum of 100 queries are allowed, each 4096 characters long. You may filter on the following attributes: name

search
string
Search term to filter your list results. Max length: 256 chars.

Response
Endpoint

GET /databases
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.list(
queries = [], # optional
search = '<SEARCH>' # optional
)
Create database
Create a new Database.

Request
databaseId
string
required
Unique Id. Choose a custom ID or generate a random ID with ID.unique(). Valid chars are a-z, A-Z, 0-9, period, hyphen, and underscore. Can't start with a special char. Max length is 36 chars.

name
string
required
Database name. Max length: 128 chars.

enabled
boolean
Is the database enabled? When set to 'disabled', users cannot access the database but Server SDKs with an API key can still read and write to the database. No data is lost when this is toggled.

Response
Endpoint

POST /databases
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create(
database_id = '<DATABASE_ID>',
name = '<NAME>',
enabled = False # optional
)
Get database
Get a database by its unique ID. This endpoint response returns a JSON object with the database metadata.

Request
databaseId
string
required
Database ID.

Response
Endpoint

GET /databases/{databaseId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.get(
database_id = '<DATABASE_ID>'
)
Update database
Update a database by its unique ID.

Request
databaseId
string
required
Database ID.

name
string
required
Database name. Max length: 128 chars.

enabled
boolean
Is database enabled? When set to 'disabled', users cannot access the database but Server SDKs with an API key can still read and write to the database. No data is lost when this is toggled.

Response
Endpoint

PUT /databases/{databaseId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update(
database_id = '<DATABASE_ID>',
name = '<NAME>',
enabled = False # optional
)
Delete database
Delete a database by its unique ID. Only API keys with with databases.write scope can delete a database.

Request
databaseId
string
required
Database ID.

Response
Endpoint

DELETE /databases/{databaseId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.delete(
database_id = '<DATABASE_ID>'
)
List collections
Get a list of all collections that belong to the provided databaseId. You can use the search parameter to filter your results.

Request
databaseId
string
required
Database ID.

queries
array
Array of query strings generated using the Query class provided by the SDK. Learn more about queries. Maximum of 100 queries are allowed, each 4096 characters long. You may filter on the following attributes: name, enabled, documentSecurity

search
string
Search term to filter your list results. Max length: 256 chars.

Response
Endpoint

GET /databases/{databaseId}/collections
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.list_collections(
database_id = '<DATABASE_ID>',
queries = [], # optional
search = '<SEARCH>' # optional
)
Create collection
Create a new Collection. Before using this route, you should create a new database resource using either a server integration API or directly from your database console.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Unique Id. Choose a custom ID or generate a random ID with ID.unique(). Valid chars are a-z, A-Z, 0-9, period, hyphen, and underscore. Can't start with a special char. Max length is 36 chars.

name
string
required
Collection name. Max length: 128 chars.

permissions
array
An array of permissions strings. By default, no user is granted with any permissions. Learn more about permissions.

documentSecurity
boolean
Enables configuring permissions for individual documents. A user needs one of document or collection level permissions to access a document. Learn more about permissions.

enabled
boolean
Is collection enabled? When set to 'disabled', users cannot access the collection but Server SDKs with and API key can still read and write to the collection. No data is lost when this is toggled.

Response
Endpoint

POST /databases/{databaseId}/collections
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_collection(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
name = '<NAME>',
permissions = ["read("any")"], # optional
document_security = False, # optional
enabled = False # optional
)
Get collection
Get a collection by its unique ID. This endpoint response returns a JSON object with the collection metadata.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID.

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.get_collection(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>'
)
Update collection
Update a collection by its unique ID.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID.

name
string
required
Collection name. Max length: 128 chars.

permissions
array
An array of permission strings. By default, the current permissions are inherited. Learn more about permissions.

documentSecurity
boolean
Enables configuring permissions for individual documents. A user needs one of document or collection level permissions to access a document. Learn more about permissions.

enabled
boolean
Is collection enabled? When set to 'disabled', users cannot access the collection but Server SDKs with and API key can still read and write to the collection. No data is lost when this is toggled.

Response
Endpoint

PUT /databases/{databaseId}/collections/{collectionId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_collection(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
name = '<NAME>',
permissions = ["read("any")"], # optional
document_security = False, # optional
enabled = False # optional
)
Delete collection
Delete a collection by its unique ID. Only users with write permissions have access to delete this resource.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID.

Response
Endpoint

DELETE /databases/{databaseId}/collections/{collectionId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.delete_collection(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>'
)
List attributes
List attributes in the collection.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

queries
array
Array of query strings generated using the Query class provided by the SDK. Learn more about queries. Maximum of 100 queries are allowed, each 4096 characters long. You may filter on the following attributes: key, type, size, required, array, status, error

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}/attributes
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.list_attributes(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
queries = [] # optional
)
Create boolean attribute
Create a boolean attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
boolean
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/boolean
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_boolean_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = False, # optional
array = False # optional
)
Update boolean attribute
Update a boolean attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
boolean
required
Default value for attribute when not provided. Cannot be set when attribute is required.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/boolean/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_boolean_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = False,
new_key = '' # optional
)
Create datetime attribute
Create a date time attribute according to the ISO 8601 standard.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
Default value for the attribute in ISO 8601 format. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/datetime
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_datetime_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = '', # optional
array = False # optional
)
Update dateTime attribute
Update a date time attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
required
Default value for attribute when not provided. Cannot be set when attribute is required.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/datetime/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_datetime_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = '',
new_key = '' # optional
)
Create email attribute
Create an email attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/email
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_email_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = 'email@example.com', # optional
array = False # optional
)
Update email attribute
Update an email attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
required
Default value for attribute when not provided. Cannot be set when attribute is required.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/email/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_email_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = 'email@example.com',
new_key = '' # optional
)
Create enum attribute
Create an enumeration attribute. The elements param acts as a white-list of accepted values for this attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

elements
array
required
Array of elements in enumerated type. Uses length of longest element to determine size. Maximum of 100 elements are allowed, each 255 characters long.

required
boolean
required
Is attribute required?

default
string
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/enum
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_enum_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
elements = [],
required = False,
default = '<DEFAULT>', # optional
array = False # optional
)
Update enum attribute
Update an enum attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

elements
array
required
Array of elements in enumerated type. Uses length of longest element to determine size. Maximum of 100 elements are allowed, each 255 characters long.

required
boolean
required
Is attribute required?

default
string
required
Default value for attribute when not provided. Cannot be set when attribute is required.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/enum/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_enum_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
elements = [],
required = False,
default = '<DEFAULT>',
new_key = '' # optional
)
Create float attribute
Create a float attribute. Optionally, minimum and maximum values can be provided.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

min
number
Minimum value to enforce on new documents

max
number
Maximum value to enforce on new documents

default
number
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/float
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_float_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
min = None, # optional
max = None, # optional
default = None, # optional
array = False # optional
)
Update float attribute
Update a float attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
number
required
Default value for attribute when not provided. Cannot be set when attribute is required.

min
number
Minimum value to enforce on new documents

max
number
Maximum value to enforce on new documents

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/float/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_float_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
min = None,
max = None,
default = None,
new_key = '' # optional
)
Create integer attribute
Create an integer attribute. Optionally, minimum and maximum values can be provided.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

min
integer
Minimum value to enforce on new documents

max
integer
Maximum value to enforce on new documents

default
integer
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/integer
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_integer_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
min = None, # optional
max = None, # optional
default = None, # optional
array = False # optional
)
Update integer attribute
Update an integer attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
integer
required
Default value for attribute when not provided. Cannot be set when attribute is required.

min
integer
Minimum value to enforce on new documents

max
integer
Maximum value to enforce on new documents

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/integer/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_integer_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
min = None,
max = None,
default = None,
new_key = '' # optional
)
Create IP address attribute
Create IP address attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/ip
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_ip_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = '', # optional
array = False # optional
)
Update IP address attribute
Update an ip attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
required
Default value for attribute when not provided. Cannot be set when attribute is required.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/ip/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_ip_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = '',
new_key = '' # optional
)
Create relationship attribute
Create relationship attribute. Learn more about relationship attributes.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

relatedCollectionId
string
required
Related Collection ID. You can create a new collection using the Database service server integration.

type
string
required
Relation type

twoWay
boolean
Is Two Way?

key
string
Attribute Key.

twoWayKey
string
Two Way Attribute Key.

onDelete
string
Constraints option

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/relationship
Python

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.enums import RelationshipType

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_relationship_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
related_collection_id = '<RELATED_COLLECTION_ID>',
type = RelationshipType.ONETOONE,
two_way = False, # optional
key = '', # optional
two_way_key = '', # optional
on_delete = RelationMutate.CASCADE # optional
)
Create string attribute
Create a string attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

size
integer
required
Attribute size for text attributes, in number of characters.

required
boolean
required
Is attribute required?

default
string
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

encrypt
boolean
Toggle encryption for the attribute. Encryption enhances security by not storing any plain text values in the database. However, encrypted attributes cannot be queried.

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/string
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_string_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
size = 1,
required = False,
default = '<DEFAULT>', # optional
array = False, # optional
encrypt = False # optional
)
Update string attribute
Update a string attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
required
Default value for attribute when not provided. Cannot be set when attribute is required.

size
integer
Maximum size of the string attribute.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/string/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_string_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = '<DEFAULT>',
size = 1, # optional
new_key = '' # optional
)
Create URL attribute
Create a URL attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
Default value for attribute when not provided. Cannot be set when attribute is required.

array
boolean
Is attribute an array?

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/attributes/url
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_url_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = 'https://example.com', # optional
array = False # optional
)
Update URL attribute
Update an url attribute. Changing the default value will not update already existing documents.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

required
boolean
required
Is attribute required?

default
string
required
Default value for attribute when not provided. Cannot be set when attribute is required.

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/url/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_url_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
required = False,
default = 'https://example.com',
new_key = '' # optional
)
Get attribute
Get attribute by ID.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}/attributes/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.get_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = ''
)
Delete attribute
Deletes an attribute.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

Response
Endpoint

DELETE /databases/{databaseId}/collections/{collectionId}/attributes/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.delete_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = ''
)
Update relationship attribute
Update relationship attribute. Learn more about relationship attributes.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Attribute Key.

onDelete
string
Constraints option

newKey
string
New attribute key.

Response
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/attributes/{key}/relationship
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.update_relationship_attribute(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
on_delete = RelationMutate.CASCADE, # optional
new_key = '' # optional
)
List documents
Get a list of all the user's documents in a given collection. You can use the query params to filter your results.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

queries
array
Array of query strings generated using the Query class provided by the SDK. Learn more about queries. Maximum of 100 queries are allowed, each 4096 characters long.

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}/documents
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_session('') # The user session to authenticate with

databases = Databases(client)

result = databases.list_documents(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
queries = [] # optional
)
Create document
Create a new Document. Before using this route, you should create a new collection resource using either a server integration API or directly from your database console.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration. Make sure to define attributes before creating documents.

documentId
string
required
Document ID. Choose a custom ID or generate a random ID with ID.unique(). Valid chars are a-z, A-Z, 0-9, period, hyphen, and underscore. Can't start with a special char. Max length is 36 chars.

data
object
required
Document data as JSON object.

permissions
array
An array of permissions strings. By default, only the current user is granted all permissions. Learn more about permissions.

Response
Rate limits
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/documents
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_session('') # The user session to authenticate with

databases = Databases(client)

result = databases.create_document(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
document_id = '<DOCUMENT_ID>',
data = {},
permissions = ["read("any")"] # optional
)
Get document
Get a document by its unique ID. This endpoint response returns a JSON object with the document data.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

documentId
string
required
Document ID.

queries
array
Array of query strings generated using the Query class provided by the SDK. Learn more about queries. Maximum of 100 queries are allowed, each 4096 characters long.

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}/documents/{documentId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_session('') # The user session to authenticate with

databases = Databases(client)

result = databases.get_document(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
document_id = '<DOCUMENT_ID>',
queries = [] # optional
)
Update document
Update a document by its unique ID. Using the patch method you can pass only specific fields that will get updated.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID.

documentId
string
required
Document ID.

data
object
Document data as JSON object. Include only attribute and value pairs to be updated.

permissions
array
An array of permissions strings. By default, the current permissions are inherited. Learn more about permissions.

Response
Rate limits
Endpoint

PATCH /databases/{databaseId}/collections/{collectionId}/documents/{documentId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_session('') # The user session to authenticate with

databases = Databases(client)

result = databases.update_document(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
document_id = '<DOCUMENT_ID>',
data = {}, # optional
permissions = ["read("any")"] # optional
)
Delete document
Delete a document by its unique ID.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

documentId
string
required
Document ID.

Response
Rate limits
Endpoint

DELETE /databases/{databaseId}/collections/{collectionId}/documents/{documentId}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_session('') # The user session to authenticate with

databases = Databases(client)

result = databases.delete_document(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
document_id = '<DOCUMENT_ID>'
)
List indexes
List indexes in the collection.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

queries
array
Array of query strings generated using the Query class provided by the SDK. Learn more about queries. Maximum of 100 queries are allowed, each 4096 characters long. You may filter on the following attributes: key, type, status, attributes, error

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}/indexes
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.list_indexes(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
queries = [] # optional
)
Create index
Creates an index on the attributes listed. Your index should include all the attributes you will query in a single request. Attributes can be key, fulltext, and unique.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Index Key.

type
string
required
Index type.

attributes
array
required
Array of attributes to index. Maximum of 100 attributes are allowed, each 32 characters long.

orders
array
Array of index orders. Maximum of 100 orders are allowed.

Response
Endpoint

POST /databases/{databaseId}/collections/{collectionId}/indexes
Python

from appwrite.client import Client
from appwrite.services.databases import Databases
from appwrite.enums import IndexType

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.create_index(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = '',
type = IndexType.KEY,
attributes = [],
orders = [] # optional
)
Get index
Get index by ID.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Index Key.

Response
Endpoint

GET /databases/{databaseId}/collections/{collectionId}/indexes/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.get_index(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = ''
)
Delete index
Delete an index.

Request
databaseId
string
required
Database ID.

collectionId
string
required
Collection ID. You can create a new collection using the Database service server integration.

key
string
required
Index Key.

Response
Endpoint

DELETE /databases/{databaseId}/collections/{collectionId}/indexes/{key}
Python

from appwrite.client import Client
from appwrite.services.databases import Databases

client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1') # Your API Endpoint
client.set_project('<YOUR_PROJECT_ID>') # Your project ID
client.set_key('<YOUR_API_KEY>') # Your secret API key

databases = Databases(client)

result = databases.delete_index(
database_id = '<DATABASE_ID>',
collection_id = '<COLLECTION_ID>',
key = ''
)
On This Page
List databases
Create database
Get database
Update database
Delete database
List collections
Create collection
Get collection
Update collection
Delete collection
List attributes
Create boolean attribute
Update boolean attribute
Create datetime attribute
Update dateTime attribute
Create email attribute
Update email attribute
Create enum attribute
Update enum attribute
Create float attribute
Update float attribute
Create integer attribute
Update integer attribute
Create IP address attribute
Update IP address attribute
Create relationship attribute
Create string attribute
Update string attribute
Create URL attribute
Update URL attribute
Get attribute
Delete attribute
Update relationship attribute
List documents
Create document
Get document
Update document
Delete document
List indexes
Create index
Get index
Delete index
Back to top
Support
Status
Copyright © 2025 Appwrite
Search in docs
Recommended
Databases API Reference - Docs - Appwrite
