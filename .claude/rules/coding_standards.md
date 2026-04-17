# Coding Standards

**Purpose:** Define consistent code style across all programming languages used in this project.  
**Update Frequency:** Review quarterly or when adding new language support.  
**Enforcement:** Manual review for now; can integrate linters/formatters.

---

## 🎯 Universal Principles (All Languages)

These apply regardless of what language you're using:

### 1. Clarity Over Cleverness
```
❌ AVOID: Dense, hard-to-read code
   x = [i for i in range(n) if i%2==0 and i**2<100]

✅ PREFER: Clear intent
   even_numbers = [i for i in range(n) if is_even(i) and is_small_square(i)]
```

### 2. Self-Documenting Code
```
❌ AVOID: Unclear variable names
   def p(l): return sum(l)/len(l)

✅ PREFER: Descriptive names
   def calculate_average(numbers): return sum(numbers) / len(numbers)
```

### 3. Single Responsibility
- Each function does ONE thing
- Each module has ONE purpose
- Each class has ONE reason to change

### 4. Fail Fast & Explicitly
```
❌ AVOID: Silent failures
   result = try_operation()  # Did it fail? Who knows?

✅ PREFER: Explicit error handling
   try:
       result = perform_operation()
   except ValidationError as e:
       logger.error(f"Validation failed: {e}")
       raise
```

### 5. Comments Explain "Why", Not "What"
```
❌ AVOID: Obvious comments
   x = x + 1  # Increment x

✅ PREFER: Intention comments
   # Skip the first element which is always a header row
   x = x + 1
```

### 6. DRY (Don't Repeat Yourself)
- Extract repeated code into functions
- Create reusable utilities
- Use libraries instead of reimplementing

### 7. KISS (Keep It Simple, Stupid)
- Avoid over-engineering
- Use the simplest approach that solves the problem
- Premature optimization kills readability

---

## 📋 Language-Specific Standards

### Python

#### Style
- **Format:** Follow PEP 8
- **Formatter:** Use `black` or `autopep8`
- **Linter:** Use `pylint` or `flake8`
- **Indentation:** 4 spaces (never tabs)
- **Line length:** 88 characters (black default)
- **Imports:** Group as: stdlib → third-party → local

#### Naming
```python
# Classes: PascalCase
class DataProcessor:
    pass

# Functions/methods: snake_case
def process_data(input_file):
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private: prefix with _
def _internal_helper():
    pass
```

#### Type Hints (Python 3.6+)
```python
# ✅ Add type hints to all functions
def fetch_user(user_id: int) -> dict:
    """Fetch user by ID.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        User data dictionary
    """
    pass

# ✅ Use for complex data
from typing import List, Optional, Dict

def process_items(items: List[str]) -> Optional[Dict[str, int]]:
    pass
```

#### Error Handling
```python
# ❌ AVOID: Bare except
try:
    data = fetch_data()
except:
    pass

# ✅ DO: Specific exceptions
try:
    data = fetch_data()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
except ValueError as e:
    logger.warning(f"Invalid data: {e}")
    return None
```

#### Testing
```python
# Test file location: next to implementation
# implementation: src/processor.py
# tests: tests/test_processor.py

# Test naming: test_[function_name]_[scenario]
def test_process_data_with_valid_input():
    assert process_data(VALID_INPUT) == EXPECTED_OUTPUT

def test_process_data_raises_on_invalid_input():
    with pytest.raises(ValueError):
        process_data(INVALID_INPUT)
```

---

### JavaScript / TypeScript

#### Style
- **Format:** Use `prettier`
- **Linter:** Use `eslint`
- **Indentation:** 2 spaces
- **Line length:** 100 characters
- **Semicolons:** Always include
- **Quotes:** Use double quotes (`"`)

#### Naming
```javascript
// Classes/Constructors: PascalCase
class UserService {
  constructor() {}
}

// Functions/variables: camelCase
const fetchUser = (userId) => {
  return users.find(u => u.id === userId);
}

// Constants: UPPER_SNAKE_CASE
const MAX_RETRIES = 3;
const API_TIMEOUT_MS = 5000;

// Private/internal: prefix with _
const _internalHelper = () => {
  return Math.random();
}
```

#### TypeScript Specifics
```typescript
// ✅ Always add type annotations
interface User {
  id: number;
  name: string;
  email?: string;  // Optional field
}

const fetchUser = async (userId: number): Promise<User> => {
  const response = await fetch(`/api/users/${userId}`);
  return response.json();
}

// ✅ Use strict mode in tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true
  }
}
```

#### Error Handling
```javascript
// ❌ AVOID: Unhandled promises
fetch(url)
  .then(r => r.json())
  .then(data => process(data));

// ✅ DO: Proper error handling
try {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  
  const data = await response.json();
  await process(data);
} catch (error) {
  logger.error(`Processing failed: ${error.message}`);
  throw error;
}
```

#### Testing
```javascript
// Test file location: same directory, .test.js suffix
// implementation: src/processor.js
// tests: src/processor.test.js

// Test naming: descriptive, reads like documentation
describe("UserService", () => {
  test("should fetch user by ID when user exists", () => {
    const user = userService.findById(123);
    expect(user).toEqual({ id: 123, name: "John" });
  });

  test("should return null when user does not exist", () => {
    const user = userService.findById(999);
    expect(user).toBeNull();
  });
});
```

---

### Go

#### Style
- **Format:** Use `gofmt` (or `goimports` for imports)
- **Linter:** Use `golangci-lint`
- **Indentation:** Tabs (enforced by `gofmt`)
- **Line length:** 100 characters
- **Error handling:** Explicit (no exceptions)

#### Naming
```go
// Packages: lowercase, single word
package processor

// Exported types/functions: PascalCase
type DataProcessor struct {
    data []string
}

func (p *DataProcessor) Process() error {
    return nil
}

// Unexported (private): camelCase
func (p *DataProcessor) internalHelper() {
    // ...
}

// Constants: PascalCase
const (
    MaxRetries = 3
    DefaultTimeout = 30 * time.Second
)
```

#### Error Handling
```go
// ✅ GO style: explicit error returns
func FetchData(url string) ([]byte, error) {
    resp, err := http.Get(url)
    if err != nil {
        return nil, fmt.Errorf("fetch failed: %w", err)
    }
    defer resp.Body.Close()
    
    if resp.StatusCode != 200 {
        return nil, fmt.Errorf("unexpected status: %d", resp.StatusCode)
    }
    
    return io.ReadAll(resp.Body)
}

// ✅ Usage: Always check errors
data, err := FetchData(url)
if err != nil {
    log.Printf("Error: %v", err)
    return err
}
```

#### Testing
```go
// Test file location: same package, _test.go suffix
// implementation: processor.go
// tests: processor_test.go

// Test naming: Test[FunctionName]
func TestProcessWithValidInput(t *testing.T) {
    processor := NewProcessor()
    result := processor.Process("valid_input")
    if result != "expected_output" {
        t.Errorf("got %q, want %q", result, "expected_output")
    }
}
```

---

### Java

#### Style
- **Format:** Use `google-java-format`
- **Linter:** Use `checkstyle`
- **Indentation:** 2 or 4 spaces (consistent)
- **Line length:** 100 characters
- **Braces:** Opening brace on same line

#### Naming
```java
// Classes/Interfaces: PascalCase
public class UserService {
    // ...
}

public interface DataProcessor {
    // ...
}

// Methods/variables: camelCase
private String userName;

public String getUserName() {
    return userName;
}

// Constants: UPPER_SNAKE_CASE
public static final int MAX_RETRIES = 3;
private static final String CONFIG_FILE = "config.properties";
```

#### Error Handling
```java
// ✅ Use checked exceptions for recoverable errors
public List<User> loadUsers(String filePath) throws IOException {
    try {
        return parseUserFile(filePath);
    } catch (FileNotFoundException e) {
        logger.error("File not found: " + filePath, e);
        throw new IOException("Could not load users", e);
    }
}

// ✅ Use unchecked exceptions for programming errors
if (userId <= 0) {
    throw new IllegalArgumentException("userId must be positive");
}
```

#### Testing
```java
// Test file location: parallel source structure
// implementation: src/main/java/com/example/UserService.java
// tests: src/test/java/com/example/UserServiceTest.java

// Test naming: test[MethodName][Scenario]
@Test
public void testFetchUserReturnsUserWhenExists() {
    User user = userService.fetchUser(123);
    assertEquals("John", user.getName());
}

@Test
public void testFetchUserThrowsWhenNotExists() {
    assertThrows(UserNotFoundException.class,
        () -> userService.fetchUser(999));
}
```

---

### C

#### Style
- **Format:** Use `clang-format`
- **Linter:** Use `splint` or `cppcheck`
- **Indentation:** 4 spaces
- **Line length:** 80 characters
- **Braces:** Opening brace on new line (K&R style) or same line (1TBS)

#### Naming
```c
// Functions: snake_case
void process_data(const char *input);

// Structs: snake_case with _t suffix for types
typedef struct {
    int id;
    char name[256];
} user_t;

// Constants: UPPER_SNAKE_CASE
#define MAX_USERS 1000
#define DEFAULT_TIMEOUT_MS 5000

// Private static: prefix with _
static void _internal_helper(void);
```

#### Error Handling
```c
// ✅ Explicit error returns (C has no exceptions)
int read_file(const char *path, char *buffer, size_t size) {
    FILE *file = fopen(path, "r");
    if (file == NULL) {
        perror("fopen failed");
        return -1;
    }
    
    size_t read = fread(buffer, 1, size, file);
    fclose(file);
    return (read > 0) ? (int)read : -1;
}

// ✅ Check return values
char buffer[1024];
if (read_file("data.txt", buffer, sizeof(buffer)) < 0) {
    fprintf(stderr, "Failed to read file\n");
    return EXIT_FAILURE;
}
```

#### Testing
```c
// Use a framework like Unity, CUnit, or CMocka
// Test file location: tests/ directory
// tests/test_processor.c

void test_process_data_returns_expected_output(void) {
    const char *input = "test";
    char *result = process_data(input);
    TEST_ASSERT_EQUAL_STRING("test_processed", result);
    free(result);
}
```

---

## 🔄 File Organization (All Languages)

### Project Structure
```
project/
├── .claude/                     # Claude knowledge base (don't modify in code)
├── src/                         # Source code
│   ├── main/                    # Production code
│   │   ├── core/               # Core business logic
│   │   ├── utils/              # Utilities & helpers
│   │   ├── config/             # Configuration
│   │   └── models/             # Data models/structs
│   └── test/                    # Test code
│       ├── unit/               # Unit tests
│       ├── integration/        # Integration tests
│       └── fixtures/           # Test data
├── docs/                        # Project documentation
├── .env.example                 # Environment template
├── README.md                    # Project overview
└── [language-specific]          # package.json, go.mod, pom.xml, etc.
```

### Within a Module
```
module/
├── handler.py                   # Public interface
├── processor.py                 # Business logic
├── models.py                    # Data structures
├── utils.py                     # Utilities
├── constants.py                 # Constants
├── logger.py                    # Logging config
└── test_*.py                    # Tests
```

---

## ✅ Testing Standards (All Languages)

### Coverage Requirements
```
- Minimum: 70% code coverage
- Target: 80%+ for critical paths
- Measure: Use language-specific tools
  - Python: coverage.py
  - JS: Jest/NYC
  - Go: go test -cover
  - Java: JaCoCo
```

### Test Naming
```
test_[function/method_name]_[scenario]_[expected_result]

Examples:
- test_calculate_sum_with_positive_numbers_returns_correct_total
- test_parse_json_with_invalid_input_raises_error
- test_cache_get_after_set_returns_value
```

### Test Organization
```
✅ Arrange-Act-Assert pattern
def test_something():
    # Arrange: Set up test data
    input_data = {"name": "John", "age": 30}
    
    # Act: Call the function
    result = process(input_data)
    
    # Assert: Check the result
    assert result == expected_value
```

---

## 🚫 What NOT to Do (Anti-Patterns)

### Magic Numbers & Strings
```
❌ AVOID
if (retries > 5) { ... }
let timeout = 3000;

✅ DO
const MAX_RETRIES = 5;
const DEFAULT_TIMEOUT_MS = 3000;
```

### God Objects/Functions
```
❌ AVOID: 500-line function doing everything

✅ DO: Split into multiple small functions
def process_user_data(user):
    user = validate_user(user)
    user = enrich_user(user)
    return save_user(user)
```

### Deeply Nested Code
```
❌ AVOID
if condition1:
    if condition2:
        if condition3:
            if condition4:
                do_something()

✅ DO: Early returns (guard clauses)
if not condition1:
    return
if not condition2:
    return
if not condition3:
    return
do_something()
```

### Silent Failures
```
❌ AVOID
try:
    risky_operation()
except:
    pass

✅ DO
try:
    risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Commented-Out Code
```
❌ AVOID
# this is what we used before
# if something:
#     do_old_way()

✅ DO: Delete it (version control keeps history)
# New implementation
if something:
    do_new_way()
```

---

## 🔍 Code Review Checklist

Use this when reviewing code (yours or others'):

- [ ] **Clarity:** Can someone unfamiliar understand it in 5 minutes?
- [ ] **Naming:** Are all names clear and following conventions?
- [ ] **Tests:** Are there tests covering happy path + error cases?
- [ ] **Error handling:** Does it handle errors explicitly?
- [ ] **Duplication:** Is there repeated code that could be extracted?
- [ ] **Complexity:** Is it as simple as possible?
- [ ] **Comments:** Do they explain *why*, not *what*?
- [ ] **Types/Hints:** Are types/type hints present where needed?
- [ ] **Performance:** Any obvious performance issues?
- [ ] **Security:** Any security concerns (SQL injection, XSS, etc.)?
- [ ] **Dependencies:** Are external dependencies justified?
- [ ] **Backwards compatibility:** Does it break existing code?

---

## 🛠️ Tools & Automation

### Formatters (Auto-fix formatting)
```bash
# Python
black .                    # Format entire project
black file.py            # Format single file

# JavaScript/TypeScript
npx prettier --write .   # Format entire project

# Go
gofmt -w .               # Format entire project

# Java
google-java-format -i src/  # Format in-place

# C
clang-format -i *.c *.h  # Format in-place
```

### Linters (Find style/logic issues)
```bash
# Python
pylint src/
flake8 src/

# JavaScript
npm run lint

# Go
golangci-lint run

# Java
mvn checkstyle:check

# C
splint src/
```

### Test Runners
```bash
# Python
pytest -v

# JavaScript
npm test

# Go
go test ./...

# Java
mvn test

# C
ctest  # If using CMake
```

---

## 📏 Metrics to Track

| Metric | Tool | Target | Action if High |
|--------|------|--------|---|
| **Test Coverage** | coverage.py, Jest, go test | 80%+ | Add tests for uncovered paths |
| **Cyclomatic Complexity** | pylint, radon, sonarqube | <10 per function | Split into smaller functions |
| **Code Duplication** | radon, sonarqube | <3% | Extract to reusable functions |
| **Lint Warnings** | pylint, eslint | 0 | Fix or suppress with comment |
| **Test Execution Time** | CI logs | <5 min | Optimize slow tests |

---

## 🔄 Enforcement

### Pre-commit
```bash
# Run formatters and linters before committing
# Git hook: .git/hooks/pre-commit

#!/bin/bash
# Format
black .
npx prettier --write .

# Lint
pylint src/
npm run lint

# Test
pytest
npm test

# Commit only if all pass
```

### CI/CD
```yaml
# In your CI pipeline, fail if:
- Linter warnings > threshold
- Test coverage < 80%
- Tests don't pass
- Formatting issues found
```

---

## 📚 Additional Resources

- **Python:** [PEP 8 Style Guide](https://pep8.org/)
- **JavaScript:** [Google JavaScript Guide](https://google.github.io/styleguide/javascriptguide.html)
- **Go:** [Effective Go](https://golang.org/doc/effective_go)
- **Java:** [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
- **C:** [Linux Kernel Coding Style](https://www.kernel.org/doc/html/latest/process/coding-style.html)

---

**Last Updated:** YYYY-MM-DD  
**Review Schedule:** Quarterly or when adding new language support
