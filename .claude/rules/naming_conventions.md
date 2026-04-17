# Naming Conventions

**Purpose:** Establish consistent naming patterns across all code.  
**Scope:** Files, classes, functions, variables, databases, APIs.  
**Applied To:** All programming languages used in this project.  
**Enforcement:** Code review, linters (optional).

---

## 🎯 Naming Philosophy

### General Principles

1. **Clarity Over Cleverness**
   - ❌ `f`, `x`, `tmp`, `data` (too generic)
   - ✅ `user_count`, `email_parser`, `retry_attempts` (clear intent)

2. **Pronounceable Names**
   - ❌ `prcss_d8`, `usr_mgr` (abbreviations)
   - ✅ `process_data`, `user_manager` (readable)

3. **Searchable Names**
   - ❌ Single letter variables in large functions
   - ✅ Full names that can be searched in IDE

4. **No Misleading Names**
   - ❌ `get_user_data()` that actually updates the database
   - ✅ `fetch_user_data()` or `update_user_data()` (intention clear)

5. **Domain Language**
   - Use terminology from your domain
   - Example: If you work with emails, use `recipient`, `sender`, not `user1`, `user2`

6. **Avoid Hungarian Notation**
   - ❌ `strName`, `intCount`, `boolActive` (type in name)
   - ✅ `name`, `count`, `is_active` (type from context/hints)

---

## 📂 File & Directory Naming

### General Rules

```
✅ CORRECT:        ❌ AVOID:
lowercase          UPPERCASE
hyphen-separated   snake_case_in_filenames
descriptive        single_letters
```

### Python Files

```
✅ CORRECT:
data_processor.py
email_handler.py
user_service.py
test_user_service.py

❌ AVOID:
DataProcessor.py   (Use PascalCase for class names, not files)
Userservice.py     (Inconsistent casing)
processor.py       (Too vague)
test.py            (Unclear what's being tested)
```

### JavaScript/TypeScript Files

```
✅ CORRECT:
data-processor.ts
email-handler.js
user-service.ts
user-service.test.ts

❌ AVOID:
DataProcessor.ts   (Use kebab-case for files)
userservice.ts     (Missing separator)
processor.js       (Too generic)
```

### C Files

```
✅ CORRECT:
data_processor.c
email_handler.h
user_service.c

❌ AVOID:
DataProcessor.c    (Use snake_case)
processor.c        (Too generic)
```

### Go Files

```
✅ CORRECT:
data_processor.go
email_handler.go
user_service.go

❌ AVOID:
dataprocessor.go   (Missing separator)
DataProcessor.go   (Go uses lowercase filenames)
processor.go       (Too generic)
```

### Directory Structure

```
project/
├── src/
│   ├── core/              # Core business logic
│   ├── utils/             # Utility functions
│   ├── models/            # Data models/schemas
│   ├── handlers/          # API handlers (if applicable)
│   ├── services/          # Business services
│   ├── integrations/      # External service integrations
│   └── config/            # Configuration
├── tests/
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test data
├── docs/
│   ├── api/               # API documentation
│   └── architecture/      # Architecture diagrams
└── scripts/               # Utility scripts
```

---

## 🏛️ Classes & Types

### General Rules

- **PascalCase** (CapitalizedWords)
- **Nouns** (describes what the thing IS)
- **Singular** unless it's a collection
- **No type in the name** (unless exceptional)

### Python Classes

```
✅ CORRECT:
class UserService:
    pass

class DataProcessor:
    pass

class CacheManager:
    pass

class HTTPClient:
    pass

class JSONParser:
    pass

❌ AVOID:
class user_service:     (snake_case)
class Userservice:      (Inconsistent)
class user:             (Too generic)
class US:               (Too abbreviated)
class DataProcessorImpl: (Avoid "Impl" suffix)
```

### Python Type Hints

```
✅ CORRECT:
from typing import List, Dict, Optional, Union

def process_users(users: List[User]) -> Dict[str, int]:
    pass

def fetch_data(user_id: int) -> Optional[User]:
    pass

❌ AVOID:
def process_users(users):           (No type hint)
def process_users(users: list):     (lowercase)
```

### Go Interfaces

```
✅ CORRECT:
type Reader interface {
    Read(p []byte) (n int, err error)
}

type DataProcessor interface {
    Process(input []byte) ([]byte, error)
}

❌ AVOID:
type reader interface { }  (lowercase)
type IDataProcessor ...    (Avoid "I" prefix)
```

### Go Structs

```
✅ CORRECT:
type User struct {
    ID        int
    Email     string
    CreatedAt time.Time
}

type EmailConfig struct {
    Host     string
    Port     int
    Username string
}

❌ AVOID:
type user struct { }       (lowercase)
type USER struct { }       (UPPERCASE)
type User_Data struct { }  (underscore in name)
```

### Java Classes

```
✅ CORRECT:
public class UserService {
    // ...
}

public interface DataProcessor {
    // ...
}

public class EmailConfiguration {
    // ...
}

❌ AVOID:
public class user_service { }  (snake_case)
public class IUserService { }  (Interface prefix)
```

---

## 🔧 Functions & Methods

### General Rules

- **camelCase** (start lowercase)
- **Verbs** (describes what it DOES)
- **Start with action verb** (get, fetch, process, validate, etc.)
- **Describe what it returns** (if unclear)

### Python Functions

```
✅ CORRECT:
def get_user(user_id: int) -> User:
    """Retrieve user by ID."""
    pass

def process_data(data: List) -> Dict:
    """Process raw data and return results."""
    pass

def is_valid_email(email: str) -> bool:
    """Check if email is valid."""
    pass

def calculate_average(numbers: List[float]) -> float:
    """Calculate average of numbers."""
    pass

def send_notification(user_id: int, message: str) -> bool:
    """Send notification and return success status."""
    pass

❌ AVOID:
def GetUser():           (PascalCase)
def get():              (Too vague)
def process():          (What does it process?)
def user_data():        (Noun, not verb)
def checkEmail():       (camelCase inconsistent)
def data_processing(): (Noun phrase)
```

### Python Private Methods

```
✅ CORRECT:
def _validate_input(self, data):
    """Private method (internal use only)."""
    pass

def __init__(self):
    """Constructor."""
    pass

❌ AVOID:
def __private_method(): (Double underscore usually not needed)
def validate_input():   (Public when should be private)
```

### JavaScript/TypeScript Functions

```
✅ CORRECT:
function getUserById(userId: number): Promise<User> {
    // ...
}

const processData = async (data: any[]): Promise<any> => {
    // ...
}

function isValidEmail(email: string): boolean {
    // ...
}

async function sendNotification(userId: number, message: string): Promise<boolean> {
    // ...
}

❌ AVOID:
function GetUser() { }         (PascalCase)
function get() { }             (Too vague)
function checkEmail() { }      (verb inconsistent with "is")
const _privateFunc = () => { } (TypeScript uses private keyword)
```

### Go Functions

```
✅ CORRECT:
func GetUser(userID int) (*User, error) {
    // ...
}

func ProcessData(data []byte) ([]byte, error) {
    // ...
}

func IsValidEmail(email string) bool {
    // ...
}

func (p *Processor) Process(input []byte) error {
    // ...
}

❌ AVOID:
func get_user()            (snake_case)
func getUser()             (Go uses PascalCase for exported)
func checkEmail()          (Inconsistent verb with "Is")
```

### Go Receiver Methods

```
✅ CORRECT:
type User struct {
    id    int
    email string
}

// Receiver variable should be 1-2 letters
func (u *User) GetEmail() string {
    return u.email
}

func (p *Processor) Process() error {
    // ...
}

❌ AVOID:
func (user *User) GetEmail() { }  (Too long receiver name)
func (u User) GetEmail() { }      (Should be pointer, usually)
func (u *User) get_email() { }    (Should be PascalCase)
```

---

## 📊 Variables & Constants

### Variables - General Rules

- **camelCase** (start lowercase)
- **Descriptive** (what does it contain?)
- **Scope appropriate** (global vs local)

### Python Variables

```
✅ CORRECT:
user_count = 0
email_list = ["test@example.com"]
is_active = True
max_retries = 3
retry_count = 0
total_amount = 100.50

❌ AVOID:
UserCount = 0         (PascalCase)
u = 0                 (Single letter)
count = 0             (Ambiguous: count of what?)
user = "John"         (Vague: this is a name)
temp = []             (What's temporary?)
data = {}             (Too generic)
```

### JavaScript/TypeScript Variables

```
✅ CORRECT:
let userCount = 0;
const emailList = ["test@example.com"];
let isActive = true;
const maxRetries = 3;
let retryCount = 0;

❌ AVOID:
let UserCount = 0;    (PascalCase)
let u = 0;            (Single letter)
let count = 0;        (Ambiguous)
var temp = [];        (Never use var)
```

### Loop Variables

```
✅ CORRECT:
for user in users:
    print(user.name)

for index, item in enumerate(items):
    print(f"{index}: {item}")

for (let i = 0; i < array.length; i++) {
    const item = array[i];
}

❌ AVOID:
for u in users: pass              (Single letter)
for x, y in enumerate(items): pass (Unclear)
for (var i = 0; i < array.length; i++) { } (var instead of const/let)
```

### Constants - General Rules

- **UPPER_SNAKE_CASE**
- **At module/class level** (not scattered)
- **Grouped together**

### Python Constants

```
✅ CORRECT:
# Application Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30
API_REQUEST_TIMEOUT_MS = 5000

# Status Constants
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"

# Configuration
DATABASE_HOST = "localhost"
DATABASE_PORT = 5432

❌ AVOID:
max_retries = 3           (lowercase)
Max_Retries = 3           (Inconsistent)
MAX_RETRIES_ALLOWED = 3   (Too verbose)
TIMEOUT = 30              (Ambiguous: seconds? milliseconds?)
```

### JavaScript/TypeScript Constants

```
✅ CORRECT:
const MAX_RETRIES = 3;
const DEFAULT_TIMEOUT_MS = 5000;
const API_BASE_URL = "https://api.example.com";

const STATUS = {
    ACTIVE: "active",
    INACTIVE: "inactive"
};

❌ AVOID:
const maxRetries = 3;    (camelCase)
const max_retries = 3;   (snake_case)
```

---

## 🗄️ Database Naming

### General Rules

- **snake_case** for all identifiers
- **Plural table names** (users, not user)
- **Singular column names**
- **Descriptive** (no abbreviations)
- **Consistent timestamp naming**

### Table & Column Names

```
✅ CORRECT:
-- Tables: plural, snake_case
CREATE TABLE users (
    -- Columns: singular, snake_case
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP -- Soft delete
);

CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    permission_id INT REFERENCES permissions(id),
    created_at TIMESTAMP
);

CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    key_hash VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP
);

❌ AVOID:
CREATE TABLE User ( }           (Singular)
CREATE TABLE USERS ( }          (UPPERCASE)
CREATE TABLE tbl_users ( }      (Prefix)
CREATE TABLE user_list ( }      (Not plural)

-- Column naming
id              (Too generic)
user_id         (Foreign key: OK)
user_ID         (Inconsistent case)
user_name_and_email (Too verbose)
userData        (camelCase)
first-name      (Hyphen)
firstName       (camelCase)
firstname       (Run together)
```

### Foreign Keys & Relationships

```
✅ CORRECT:
-- Foreign key should be: [table_name_singular]_id
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),    -- Not "uid"
    post_id INT REFERENCES posts(id),    -- Not "pid"
    content TEXT,
    created_at TIMESTAMP
);

-- Many-to-many junction table
CREATE TABLE user_roles (
    user_id INT REFERENCES users(id),
    role_id INT REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

❌ AVOID:
fk_user_id         (Don't prefix with "fk_")
user_ref           (Not clear it's a reference)
uid                (Abbreviation)
```

### Timestamp Columns

```
✅ CORRECT:
created_at        -- When created
updated_at        -- Last modified
deleted_at        -- Soft delete timestamp
started_at        -- When process started
completed_at      -- When process ended
expires_at        -- When it expires
processed_at      -- When processed

❌ AVOID:
created            (Unclear: date? timestamp?)
modified           (When? unclear)
date_created       (Order: created_at is clearer)
createDate         (camelCase)
Creation_Date      (Inconsistent)
```

---

## 🔌 API & URL Naming

### Endpoint Naming

```
✅ CORRECT (RESTful):
GET    /api/users              -- List users
POST   /api/users              -- Create user
GET    /api/users/{id}         -- Get specific user
PUT    /api/users/{id}         -- Update user
DELETE /api/users/{id}         -- Delete user

GET    /api/users/{id}/posts   -- User's posts
POST   /api/users/{id}/posts   -- Create post for user

❌ AVOID:
GET    /api/GetUsers           (Action in URL)
GET    /api/getAllUsers        (Action in URL)
GET    /api/user               (Singular)
GET    /api/users/getById      (Redundant)
POST   /api/users/create       (Create is implied by POST)
```

### Query Parameters

```
✅ CORRECT:
GET /api/users?skip=10&limit=20        -- Pagination
GET /api/users?sort=created_at&order=desc
GET /api/posts?filter=active&author=john
GET /api/users?search=john

❌ AVOID:
GET /api/users?Skip=10         (PascalCase)
GET /api/users?limit_num=20    (Unnecessary suffix)
GET /api/users?sortBy=created  (camelCase)
```

### Response Fields

```
✅ CORRECT:
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-20T14:45:00Z"
}

❌ AVOID:
{
    "Id": 1,                    (PascalCase)
    "firstName": "John",        (camelCase)
    "is_Active": "true",        (String instead of boolean)
    "createdAt": "2025-01-15"   (Missing time)
}
```

---

## 🧪 Test Naming

### Test Files

```
✅ CORRECT:
test_user_service.py           (Python)
test_user_service.py           (Python with pytest)
user_service.test.ts           (TypeScript)
user_service_test.go           (Go)
UserServiceTest.java           (Java)

❌ AVOID:
test.py                        (What's being tested?)
UserServiceTest.py             (Mixed conventions)
tests.js                       (Too generic)
```

### Test Function Names

```
✅ CORRECT (Describe behavior):
def test_get_user_returns_user_when_id_exists():
    pass

def test_get_user_raises_when_id_not_found():
    pass

def test_process_data_with_empty_input_returns_empty_list():
    pass

def test_calculate_average_rounds_correctly():
    pass

function testGetUserReturnsUserWhenIdExists() {
    // ...
}

function testUserServiceThrowsWhenIdNotFound() {
    // ...
}

❌ AVOID:
def test_1():                  (Not descriptive)
def test_get_user():           (Unclear what we're testing)
def test_user():               (Unclear behavior)
def test_ok():                 (Vague)

// Missing "test" prefix
function getUserReturnsUser() { }
```

### Test Variable Names

```
✅ CORRECT:
def test_process_data():
    # Arrange: Setup
    input_data = {"name": "John", "age": 30}
    expected_output = {"name": "JOHN", "processed": True}
    
    # Act: Execute
    result = process(input_data)
    
    # Assert: Verify
    assert result == expected_output

❌ AVOID:
def test_process_data():
    x = {"name": "John"}         (Single letter)
    y = process(x)               (Unclear)
    assert y == z                (z is undefined)
```

---

## 🏷️ Boolean Variable Naming

### General Rule

- **Start with: is_, has_, can_, should_, will_**
- **Clearly true/false**

### Python Examples

```
✅ CORRECT:
is_active = True
is_deleted = False
has_permissions = True
can_delete = False
should_retry = True
will_timeout = False

is_valid_email = True
is_premium_user = False
has_children = True

❌ AVOID:
active = True              (Ambiguous)
valid = True               (Unclear what's valid)
deleted = False            (Unclear, sounds like action)
permission = True          (Singular, unclear)
retry = True               (Sounds like action)
user_type = "premium"      (Not boolean)
```

---

## 🎯 Naming by Context

### Configuration Variables

```
✅ CORRECT:
DATABASE_URL
API_KEY
API_BASE_URL
CACHE_TTL_SECONDS
MAX_RETRY_ATTEMPTS
LOG_LEVEL
DEBUG_MODE
FEATURE_FLAG_NEW_UI

❌ AVOID:
DB_URL            (Abbreviation)
key               (Too generic)
api               (Too generic)
cache             (What about cache?)
retries           (How many max?)
```

### Enumeration / Status Values

```
✅ CORRECT:
class Status:
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"

class UserRole:
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

❌ AVOID:
STATUS_A = "active"       (Use enum instead)
status_1 = "active"       (Numbered)
ACTIVE_STATUS = "active"  (Redundant)
```

---

## 🔄 Consistency Checklist

Before naming anything, check:

- [ ] **Consistency:** Does it match existing patterns?
- [ ] **Clarity:** Can someone unfamiliar understand it?
- [ ] **Searchability:** Can it be found in code search?
- [ ] **Pronounceability:** Can it be said aloud?
- [ ] **No ambiguity:** Is there one interpretation?
- [ ] **Domain appropriate:** Uses domain terminology?
- [ ] **Not misleading:** Does it accurately describe?

---

## 📚 Reference Table

| Context | Convention | Example | Avoid |
|---------|-----------|---------|-------|
| **Files** | kebab-case | `user-service.py` | `UserService.py` |
| **Classes** | PascalCase | `UserService` | `user_service` |
| **Functions** | camelCase | `getUserData()` | `get_user_data()` |
| **Variables** | camelCase | `userData` | `user_data` |
| **Constants** | UPPER_SNAKE_CASE | `MAX_RETRIES` | `max_retries` |
| **Database** | snake_case | `user_id` | `userId` |
| **Booleans** | `is_*` / `has_*` | `isActive` | `active` |
| **Tests** | descriptive | `test_get_user_returns_when_found` | `test_user` |

---

## 🔧 Enforcement

### Code Review

Check naming in all PRs. Request changes if:
- Generic names (x, data, temp)
- Misleading names
- Inconsistent with existing code
- Not following conventions

### Automated Checking

Optional linters/formatters:
```bash
# Python
pylint --name-style=snake_case src/

# JavaScript
npm run lint  # eslint with naming rules

# Go
golangci-lint run  # Checks naming conventions

# Java
mvn checkstyle:check  # Enforces naming
```

---

## 📝 Examples by Language

### Complete Example: User Processing System

**Python:**
```python
class UserDataProcessor:
    """Process user data from various sources."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.processed_users: List[User] = []
    
    def process_user_data(self, user_data: Dict) -> User:
        """Process and validate user data."""
        if not self._is_valid_user_data(user_data):
            raise ValueError("Invalid user data")
        
        return self._create_user_from_data(user_data)
    
    def _is_valid_user_data(self, data: Dict) -> bool:
        """Validate user data format."""
        return "email" in data and "name" in data
    
    def _create_user_from_data(self, data: Dict) -> User:
        """Create User object from dictionary."""
        return User(email=data["email"], name=data["name"])
```

**JavaScript/TypeScript:**
```typescript
class UserDataProcessor {
    private maxRetries: number;
    private processedUsers: User[] = [];
    
    constructor(maxRetries: number = 3) {
        this.maxRetries = maxRetries;
    }
    
    public processUserData(userData: Record<string, any>): User {
        if (!this.isValidUserData(userData)) {
            throw new Error("Invalid user data");
        }
        
        return this.createUserFromData(userData);
    }
    
    private isValidUserData(data: Record<string, any>): boolean {
        return "email" in data && "name" in data;
    }
    
    private createUserFromData(data: Record<string, any>): User {
        return new User(data.email, data.name);
    }
}
```

**Go:**
```go
type UserDataProcessor struct {
    MaxRetries    int
    ProcessedUsers []User
}

func (p *UserDataProcessor) ProcessUserData(userData map[string]interface{}) (User, error) {
    if !p.isValidUserData(userData) {
        return User{}, errors.New("invalid user data")
    }
    
    return p.createUserFromData(userData)
}

func (p *UserDataProcessor) isValidUserData(data map[string]interface{}) bool {
    _, hasEmail := data["email"]
    _, hasName := data["name"]
    return hasEmail && hasName
}

func (p *UserDataProcessor) createUserFromData(data map[string]interface{}) User {
    return User{
        Email: data["email"].(string),
        Name: data["name"].(string),
    }
}
```

---

## 🎓 Learning Resource

When naming, ask yourself:

1. **Can I say it out loud?** (Pronunciation test)
2. **Would someone understand it in 6 months?** (Longevity test)
3. **Is it searchable?** (IDE search test)
4. **Does it match similar code?** (Consistency test)
5. **Is it too clever?** (Clarity test)

If the answer is "no" to any, rename it.

---

**Last Updated:** YYYY-MM-DD  
**Review Frequency:** Quarterly or when adding new language  
**Maintainer:** [Your Name/Team]
