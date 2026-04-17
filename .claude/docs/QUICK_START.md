# Quick Start

## What is this?

**[Replace with 1-2 sentence project description]**

*Example: "Modular framework for prototyping AI automation workflows. Experiments with multi-paradigm approaches to problem-solving and data transformation."*

---

## How to Run It

### Prerequisites
```bash
# Install runtime/language (choose one based on your tech stack)
# For Python:
python --version  # Python 3.8+

# For JavaScript/TypeScript:
node --version    # Node 18+

# For Go:
go version        # Go 1.19+

# For Java:
java -version     # Java 11+
```

### Quick Start (Choose Your Path)

**Option A: Python**
```bash
pip install -r requirements.txt
python main.py
```

**Option B: Node.js / TypeScript**
```bash
npm install
npm run dev
```

**Option C: Go**
```bash
go mod download
go run main.go
```

**Option D: Java**
```bash
mvn clean install
mvn spring-boot:run
```

**Option E: Generic**
```bash
# Replace with actual startup command
./start.sh
```

---

## Key Files to Know

| File | Purpose | When to Read |
|------|---------|-------------|
| `.claude/docs/ARCHITECTURE.md` | System design, components, data flow | Planning/understanding structure |
| `.claude/memory/project_state.json` | Current status, blockers, active features | Before each session |
| `.claude/memory/session_context.md` | What's in progress, next steps | Session start |
| `.claude/rules/coding_standards.md` | Code style for your language | Before coding |
| `.claude/docs/GLOSSARY.md` | Project terminology | When unsure of terms |

---

## Useful Commands

### Testing
```bash
# Python
pytest                    # Run all tests
pytest -v               # Verbose output
pytest tests/test_*.py  # Run specific tests

# Node.js
npm test                # Run tests
npm run test:watch     # Watch mode
npm run test:coverage  # With coverage

# Go
go test ./...          # All tests
go test -v ./...       # Verbose
go test -cover ./...   # Coverage

# Java
mvn test               # Run tests
mvn test -Dtest=TestClass  # Specific test

# Generic
./test.sh              # Custom test script
```

### Development
```bash
# Python
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate      # Windows

# Node.js
npm run dev            # Development server
npm run build          # Build for production
npm run lint           # Code linting

# Go
go fmt ./...           # Format code
go vet ./...           # Vet code
go mod tidy            # Clean dependencies

# Generic
make dev               # Using Makefile
./build.sh             # Custom build
```

---

## Project Structure

```
.
├── .claude/                 # Claude Code knowledge base
│   ├── docs/               # Documentation (read these first!)
│   ├── memory/             # Session context & decisions
│   ├── rules/              # Coding standards & constraints
│   ├── patterns/           # Reusable templates
│   ├── commands/           # Automation scripts
│   └── agents/             # Agent personas
├── src/                    # Source code (rename as needed)
├── tests/                  # Test files
├── .env.example            # Environment variables template
├── README.md              # Full project documentation
└── [language-specific]    # package.json, go.mod, pom.xml, etc.
```

---

## Environment Setup

1. **Copy example config:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   ```bash
   # See .claude/config.md for all variables
   API_KEY=your_key_here
   DATABASE_URL=your_database_url
   LOG_LEVEL=debug
   ```

3. **Verify setup:**
   ```bash
   ./health-check.sh          # Or custom script
   npm run verify             # Or language equivalent
   ```

---

## Next Steps

### For Learning/Exploration
1. Read `.claude/docs/ARCHITECTURE.md` (understand design)
2. Review `.claude/memory/project_state.json` (current status)
3. Check `.claude/rules/coding_standards.md` (code style for your language)
4. Pick a small file to understand

### For Contributing
1. Read `.claude/memory/decision_log.md` (understand why things were done)
2. Check `.claude/memory/issues_tracker.md` (what needs work)
3. Review `.claude/rules/naming_conventions.md` (naming scheme)
4. Run tests to understand current state

### For Building a Feature
1. Check `.claude/memory/session_context.md` (what's in progress)
2. Review `.claude/patterns/` (copy established patterns)
3. Follow coding standards (language in `.claude/rules/`)
4. Add tests (follow test patterns in `.claude/patterns/`)

---

## Troubleshooting

### Common Issues

**"Module/Package not found"**
```bash
# Python
pip install -r requirements.txt

# Node.js
npm install

# Go
go mod download

# Java
mvn clean install
```

**"Port already in use"**
```bash
# Find what's using the port
lsof -i :3000  # macOS/Linux
netstat -ano | findstr :3000  # Windows

# Change port in .env or config
PORT=3001
```

**"Database connection failed"**
- Check `.env` has correct `DATABASE_URL`
- Verify database is running
- Check connection string format in `.claude/config.md`

**"Tests failing"**
- Ensure all dependencies installed
- Check environment variables in `.env`
- See `.claude/docs/ARCHITECTURE.md` for test setup

---

## Getting Help

| Question | Look Here |
|----------|-----------|
| "How is this built?" | `.claude/docs/ARCHITECTURE.md` |
| "What does [term] mean?" | `.claude/docs/GLOSSARY.md` |
| "Why was X designed this way?" | `.claude/memory/decision_log.md` |
| "What's broken?" | `.claude/memory/issues_tracker.md` |
| "What should I work on?" | `.claude/memory/session_context.md` |
| "What are the code rules?" | `.claude/rules/` |

---

## Quick Health Check

```bash
# Run this to verify everything works
bash .claude/commands/health-check.sh

# Or manually:
1. Import/require main module (no errors)
2. Run tests (all pass)
3. Start dev server (starts without errors)
4. Visit http://localhost:3000 (responds)
```

---

## Resources

- **Full documentation:** See `README.md`
- **Architecture deep-dive:** `.claude/docs/ARCHITECTURE.md`
- **API reference:** `.claude/docs/API.md`
- **Session notes:** `.claude/memory/session_context.md`
- **Decision history:** `.claude/memory/decision_log.md`

---

**Ready to dive in? Start with `.claude/docs/ARCHITECTURE.md`** 🚀
