#!/bin/bash
# ============================================================================
# .claude/commands/setup.sh - Project initialization and setup script
# ============================================================================
# Purpose: Initialize project environment, install dependencies
# Usage:   bash .claude/commands/setup.sh
# ============================================================================

set -e  # Exit on any error

echo "🚀 Setting up project environment..."
echo ""

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "Detected OS: $OS"
echo ""

# ============================================================================
# Python Setup
# ============================================================================
setup_python() {
    echo "📦 Setting up Python environment..."
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python3 not found. Please install Python 3.8+ first."
        exit 1
    fi
    
    python_version=$(python3 --version)
    echo "✅ Found: $python_version"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    if [ "$OS" = "windows" ]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
    
    echo "✅ Virtual environment activated"
    
    # Upgrade pip
    echo "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        echo "Installing dependencies from requirements.txt..."
        pip install -r requirements.txt
        echo "✅ Dependencies installed"
    fi
    
    if [ -f "requirements-dev.txt" ]; then
        echo "Installing dev dependencies..."
        pip install -r requirements-dev.txt
        echo "✅ Dev dependencies installed"
    fi
}

# ============================================================================
# Node.js Setup
# ============================================================================
setup_nodejs() {
    echo "📦 Setting up Node.js environment..."
    
    # Check if Node is installed
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js not found. Please install Node 18+ first."
        exit 1
    fi
    
    node_version=$(node --version)
    echo "✅ Found: $node_version"
    
    # Install dependencies
    if [ -f "package.json" ]; then
        echo "Installing npm dependencies..."
        npm install
        echo "✅ Dependencies installed"
    fi
}

# ============================================================================
# Go Setup
# ============================================================================
setup_go() {
    echo "📦 Setting up Go environment..."
    
    # Check if Go is installed
    if ! command -v go &> /dev/null; then
        echo "❌ Go not found. Please install Go 1.19+ first."
        exit 1
    fi
    
    go_version=$(go version)
    echo "✅ Found: $go_version"
    
    # Download dependencies
    echo "Downloading Go modules..."
    go mod download
    
    # Tidy up
    echo "Tidying Go modules..."
    go mod tidy
    
    echo "✅ Go modules ready"
}

# ============================================================================
# Java Setup
# ============================================================================
setup_java() {
    echo "📦 Setting up Java environment..."
    
    # Check if Java is installed
    if ! command -v javac &> /dev/null; then
        echo "❌ Java not found. Please install Java 11+ first."
        exit 1
    fi
    
    java_version=$(javac -version 2>&1)
    echo "✅ Found: $java_version"
    
    # Check for Maven
    if ! command -v mvn &> /dev/null; then
        echo "⚠️  Maven not found. Some features may not work."
        echo "Install Maven to enable: mvn clean install"
    else
        echo "Building with Maven..."
        mvn clean install
        echo "✅ Build complete"
    fi
}

# ============================================================================
# Environment Configuration
# ============================================================================
setup_environment() {
    echo ""
    echo "⚙️  Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            echo "Creating .env from .env.example..."
            cp .env.example .env
            echo "✅ Created .env (update with your values)"
        else
            echo "⚠️  No .env.example found. Create .env manually."
        fi
    else
        echo "✅ .env exists"
    fi
    
    echo ""
    echo "📋 Required environment variables (check .env):"
    # Add your required variables here
    # echo "  - DATABASE_URL"
    # echo "  - API_KEY"
    # echo "  - PORT"
}

# ============================================================================
# Database Setup (if applicable)
# ============================================================================
setup_database() {
    echo ""
    echo "🗄️  Setting up database..."
    
    # Check for migrations
    if command -v psql &> /dev/null; then
        echo "⚠️  PostgreSQL client found. Database setup needed manually."
        echo "Connect to database and run migrations:"
        echo "  psql -U postgres -d your_db -f migrations/*.sql"
    fi
    
    # Alembic for Python SQLAlchemy
    if command -v alembic &> /dev/null; then
        echo "Running Alembic migrations..."
        alembic upgrade head
        echo "✅ Database migrations complete"
    fi
}

# ============================================================================
# Git Setup
# ============================================================================
setup_git() {
    echo ""
    echo "📦 Setting up git hooks..."
    
    if [ -d ".git" ]; then
        # Create pre-commit hook (optional)
        if [ ! -f ".git/hooks/pre-commit" ]; then
            echo "Creating pre-commit hook (optional)..."
            mkdir -p .git/hooks
            cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run linters before commit
echo "Running pre-commit checks..."

# Add your checks here
# npm run lint
# black .
# go fmt ./...

echo "✅ Pre-commit checks passed"
EOF
            chmod +x .git/hooks/pre-commit
        fi
    fi
}

# ============================================================================
# Dependencies Detection & Setup
# ============================================================================
detect_and_setup() {
    echo "🔍 Detecting project type..."
    echo ""
    
    # Python
    if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
        setup_python
    fi
    
    # Node.js
    if [ -f "package.json" ]; then
        setup_nodejs
    fi
    
    # Go
    if [ -f "go.mod" ] || [ -f "go.sum" ]; then
        setup_go
    fi
    
    # Java
    if [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
        setup_java
    fi
}

# ============================================================================
# Health Check
# ============================================================================
health_check() {
    echo ""
    echo "🏥 Running health checks..."
    echo ""
    
    # Python
    if [ -f "requirements.txt" ]; then
        echo "✓ Python project detected"
        if command -v python3 &> /dev/null; then
            echo "  ✅ Python 3 available"
        fi
    fi
    
    # Node.js
    if [ -f "package.json" ]; then
        echo "✓ Node.js project detected"
        if command -v node &> /dev/null; then
            echo "  ✅ Node.js available"
        fi
        if command -v npm &> /dev/null; then
            echo "  ✅ npm available"
        fi
    fi
    
    # Go
    if [ -f "go.mod" ]; then
        echo "✓ Go project detected"
        if command -v go &> /dev/null; then
            echo "  ✅ Go available"
        fi
    fi
    
    # Java
    if [ -f "pom.xml" ]; then
        echo "✓ Java/Maven project detected"
        if command -v javac &> /dev/null; then
            echo "  ✅ Java available"
        fi
        if command -v mvn &> /dev/null; then
            echo "  ✅ Maven available"
        fi
    fi
}

# ============================================================================
# Main Setup Flow
# ============================================================================
main() {
    echo "════════════════════════════════════════════════════════════"
    echo "   Project Setup Script"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Detect and setup
    detect_and_setup
    
    # Setup environment
    setup_environment
    
    # Setup git (optional)
    setup_git
    
    # Health check
    health_check
    
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "✅ Setup complete!"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env with your configuration"
    echo "2. Run tests: bash .claude/commands/test.sh"
    echo "3. Start development: bash .claude/commands/dev.sh"
    echo ""
    echo "For more info: cat .claude/docs/QUICK_START.md"
}

# Run main
main
