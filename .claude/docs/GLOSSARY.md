# Glossary

**Purpose:** Define project-specific terms and abbreviations to avoid confusion.  
**Audience:** New team members, collaborators, future maintainers.  
**Updated:** When new terms are introduced or standardized.

---

## 📚 Core Concepts

### [Term 1]: Your Project's Fundamental Concept

**Definition:** A clear, 1-2 sentence definition of this term.

**Example:**
> In data processing contexts: The process of converting raw input into standardized format for further analysis. Example: Converting CSV to JSON.

**Related Terms:**
- Related Term 1: How it relates
- Related Term 2: How it relates

**Used In:**
- `.claude/docs/ARCHITECTURE.md`
- `.claude/rules/coding_standards.md`

**Example Usage:**
```python
# In code
processor = DataProcessor()
result = processor.term1_function()
```

**Common Mistakes:**
- ❌ Using "term1" to mean something else
- ✅ Use "term1" to mean [specific definition]

---

### [Term 2]: Another Core Concept

**Definition:** [Clear definition]

**Example:** [Concrete example from your domain]

**Related Terms:**
- Related Term: [Relationship]

**Used In:**
- [Documents where this is used]

---

## 🔤 Abbreviations

### API-Related

| Abbreviation | Full Form | Meaning | Example |
|--------------|-----------|---------|---------|
| **REST** | Representational State Transfer | Web service design pattern | REST API endpoints |
| **HTTP** | Hypertext Transfer Protocol | Protocol for web communication | HTTP 200 response |
| **JSON** | JavaScript Object Notation | Data format | `{"key": "value"}` |
| **XML** | Extensible Markup Language | Data format | `<tag>value</tag>` |
| **URL** | Uniform Resource Locator | Web address | `https://api.example.com` |
| **CORS** | Cross-Origin Resource Sharing | Security protocol | Cross-domain requests |

### Database-Related

| Abbreviation | Full Form | Meaning | Example |
|--------------|-----------|---------|---------|
| **SQL** | Structured Query Language | Database query language | SELECT * FROM users |
| **ACID** | Atomicity, Consistency, Isolation, Durability | Transaction properties | Database guarantees |
| **ORM** | Object-Relational Mapping | Abstraction layer | SQLAlchemy, Hibernate |
| **ETL** | Extract, Transform, Load | Data pipeline | Data warehouse loading |
| **OLTP** | Online Transaction Processing | Real-time database | Day-to-day operations |
| **OLAP** | Online Analytical Processing | Analytical database | Data warehousing, BI |

### Infrastructure

| Abbreviation | Full Form | Meaning | Example |
|--------------|-----------|---------|---------|
| **CI/CD** | Continuous Integration / Continuous Deployment | Automated testing & deployment | GitHub Actions |
| **AWS** | Amazon Web Services | Cloud provider | EC2 instances |
| **K8s** | Kubernetes | Container orchestration | Pod management |
| **VM** | Virtual Machine | Software computer | Docker container |
| **SSH** | Secure Shell | Remote access protocol | `ssh user@host` |
| **VPN** | Virtual Private Network | Encrypted network | Secure connection |

### Programming-Related

| Abbreviation | Full Form | Meaning | Example |
|--------------|-----------|---------|---------|
| **SOLID** | Single Responsibility, Open/Closed, Liskov, Interface, Dependency | Design principles | Clean code |
| **DRY** | Don't Repeat Yourself | Reuse code | Extract functions |
| **KISS** | Keep It Simple, Stupid | Simplicity principle | Avoid over-engineering |
| **YAGNI** | You Aren't Gonna Need It | Don't build unused features | Focus on current needs |

### Project-Specific Abbreviations

| Abbreviation | Full Form | Meaning | Example |
|--------------|-----------|---------|---------|
| **[Your Abbr 1]** | [Full form] | [What it means] | [How it's used] |
| **[Your Abbr 2]** | [Full form] | [What it means] | [How it's used] |
| **[Your Abbr 3]** | [Full form] | [What it means] | [How it's used] |

---

## 🎓 Domain-Specific Terms

### [Your Domain 1]: [Subdomain]

#### Term 1
**Definition:** [What it is]

**Context:** When working with [domain specific context]

**Example:** [Concrete example]

**Related:** [Other terms]

---

### [Your Domain 2]: [Subdomain]

#### Term 1
**Definition:** [What it is]

**Context:** [When you use it]

**Example:** [Concrete example]

---

## 📊 System Components (Short Reference)

Quick lookup for architectural components:

| Component | Purpose | Language | Status |
|-----------|---------|----------|--------|
| [Component Name 1] | [What it does] | Python/JS/Go | Stable |
| [Component Name 2] | [What it does] | Python/JS/Go | In Dev |
| [Component Name 3] | [What it does] | Python/JS/Go | Stable |

**For detailed info:** See `.claude/docs/ARCHITECTURE.md`

---

## 🔄 Process Terminology

### Development Process

**Sprint**
Definition: Time-boxed iteration of development work (typically 1-2 weeks)

**Standup**
Definition: Brief daily meeting where team shares progress and blockers

**Code Review**
Definition: Process where peers review code for quality, correctness, security

**Deployment**
Definition: Moving code from development to production environment

**Rollback**
Definition: Reverting to previous version if something breaks in production

---

### Release Management

**Release Candidate**
Definition: Version tested and ready for release; may go to production if no issues found

**Hotfix**
Definition: Urgent fix for critical bug in production

**Patch**
Definition: Minor update (e.g., v1.0.1 from v1.0.0)

**Minor Release**
Definition: New features added (e.g., v1.1.0 from v1.0.0)

**Major Release**
Definition: Significant changes, possible breaking changes (e.g., v2.0.0 from v1.0.0)

---

## 🗂️ File/Code Organization Terms

**Module**
Definition: Self-contained unit of code that provides specific functionality

**Package**
Definition: Collection of related modules

**Namespace**
Definition: Prefix that organizes code and prevents name collisions

**Import**
Definition: Bringing external code into current file for use

**Export**
Definition: Making code available for other files to import

---

## 🚨 Status & Health Terms

| Term | Meaning | Example |
|------|---------|---------|
| **Healthy** | Working as expected | Service is healthy ✅ |
| **Degraded** | Partially working, performance issues | API is degraded, slow responses ⚠️ |
| **Unhealthy** | Not working properly | Database is unhealthy, errors ❌ |
| **Stale** | Outdated, needs refresh | Cache is stale, reload needed |
| **Blocker** | Something preventing progress | Issue #5 is a blocker for Feature X |

---

## 📈 Metrics & Performance Terms

**Latency**
Definition: Time it takes to process a request (measured in milliseconds)

**Throughput**
Definition: Number of requests processed per unit time

**P50 / P95 / P99**
Definition: Performance percentiles (50th, 95th, 99th percentile response times)

**SLA**
Definition: Service Level Agreement - guaranteed uptime/performance

**SLO**
Definition: Service Level Objective - target metric we aim for

**Error Rate**
Definition: Percentage of requests that fail

**Availability**
Definition: Percentage of time service is operational

---

## 🔐 Security & Compliance Terms

**Authentication**
Definition: Verifying who you are (login)

**Authorization**
Definition: Determining what you're allowed to do (permissions)

**Encryption**
Definition: Converting data into code to prevent unauthorized access

**SSL/TLS**
Definition: Protocols for secure web communication (HTTPS)

**API Key**
Definition: Secret token used to authenticate API requests

**GDPR**
Definition: General Data Protection Regulation - EU privacy law

**CAN-SPAM**
Definition: US law regulating marketing emails

---

## 🎯 Testing Terms

**Unit Test**
Definition: Test of single function/method in isolation

**Integration Test**
Definition: Test of multiple components working together

**End-to-End Test**
Definition: Test of full system from user perspective

**Mock**
Definition: Fake object that simulates real behavior for testing

**Stub**
Definition: Simplified version of code that returns fixed values for testing

**Test Coverage**
Definition: Percentage of code paths executed by tests

---

## 🔗 Related Terms by Category

### Error Types
- Exception
- Error
- Warning
- Debug

### Data Types
- String
- Integer
- Boolean
- Array
- Object

### Time-Related
- Synchronous (happens in sequence)
- Asynchronous (happens in parallel, results later)
- Blocking (waits for completion)
- Non-blocking (returns immediately)

---

## 🔍 Common Confusion Points

### Terms Often Confused

**REST vs SOAP**
- **REST:** Simpler, HTTP-based, most modern APIs
- **SOAP:** Older, XML-based, more complex

**Microservices vs Monolith**
- **Microservices:** Multiple small independent services
- **Monolith:** Single large application

**Library vs Framework**
- **Library:** Collection of tools you call
- **Framework:** Structures your entire application

**Deploy vs Release**
- **Deploy:** Moving code to a server
- **Release:** Making it available to users (may happen after deploy)

**Cache vs Database**
- **Cache:** Fast, temporary storage (Redis, in-memory)
- **Database:** Permanent, queryable storage (PostgreSQL)

---

## 📝 Style Conventions (References)

For naming related terms, see:
- `.claude/rules/naming_conventions.md` - How to name things
- `.claude/rules/coding_standards.md` - How to write code

---

## 🔄 Term Lifecycle

### New Terms

When introducing a new term:
1. **Define it clearly** (1-2 sentences)
2. **Give an example** (concrete usage)
3. **Note related terms**
4. **Add to glossary**
5. **Update documentation** that uses it
6. **Share with team** in standup/meeting

### Deprecated Terms

Old terms that are being phased out:
- **[Old Term]** → Use **[New Term]** instead
- **[Old Term]** → Deprecated as of [Date], details in [Document]

---

## 🎓 Learning Resources

### For More Context

- **Architecture Details:** `.claude/docs/ARCHITECTURE.md`
- **API Reference:** `.claude/docs/API.md`
- **Decision Log:** `.claude/memory/decision_log.md` (why we chose certain approaches)
- **Coding Standards:** `.claude/rules/coding_standards.md`

### External Resources

- [RESTful API Design Guidelines](https://restfulapi.net/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Clean Code](https://en.wikipedia.org/wiki/Code_smell) concepts
- [Design Patterns](https://en.wikipedia.org/wiki/Software_design_pattern)

---

## ✅ Glossary Maintenance

### Before Adding

- [ ] Is this term unique to this project?
- [ ] Will people misunderstand without definition?
- [ ] Is it used in multiple documents?
- [ ] Can I explain it in 2 sentences?

### Before Using

- [ ] Is the term in the glossary?
- [ ] Am I using it consistently?
- [ ] Could someone misunderstand?
- [ ] Should I link to glossary?

---

## 📋 Full A-Z Reference

[Maintain alphabetical list as you add terms]

- **A:** [Term], [Term]
- **B:** [Term], [Term]
- **C:** [Term], [Term]
- **D:** [Term], [Term]
- ...
- **Z:** [Term], [Term]

---

**Last Updated:** YYYY-MM-DD  
**Maintained By:** [Your Name/Team]  
**Review Frequency:** As needed when new terms introduced  
**Contribution:** Add terms during code review when misunderstandings occur
