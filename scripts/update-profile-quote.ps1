# scripts/update-profile-quote.ps1
# Script to update the quote in the profile README.md and push changes to GitHub.

param(
    [string]$RepoPath = "$PSScriptRoot/../dhyan2815",
    [switch]$Force
)

# 1. Verify repository exists
$ReadmePath = Join-Path $RepoPath "README.md"
if (-not (Test-Path $ReadmePath)) {
    Write-Error "README.md not found at $ReadmePath"
    exit 1
}

# 2. Curated list of quotes — tech-stack aligned (AI/ML, agents, automation, full-stack, Python, data)
$Quotes = @(
    # AI Leaders — OpenAI / Sam Altman
    @{ Text = "Ideas are cheap and easy, and there are a lot of them."; Author = "Sam Altman" }
    @{ Text = "Move fast. Speed is one of your main advantages over large competitors."; Author = "Sam Altman" }

    # AI Leaders — Elon Musk
    @{ Text = "AI is a fundamental existential risk for human civilization."; Author = "Elon Musk" }
    @{ Text = "Making some sort of digital superintelligence seems like it could be dangerous."; Author = "Elon Musk" }

    # AI Leaders — Andrew Ng
    @{ Text = "AI is the new electricity."; Author = "Andrew Ng" }
    @{ Text = "The question is not whether AI will change your industry, but when."; Author = "Andrew Ng" }

    # AI Leaders — Others
    @{ Text = "Machines take me by surprise with great frequency."; Author = "Alan Turing" }
    @{ Text = "Intelligence is the ability to adapt to change."; Author = "Stephen Hawking" }
    @{ Text = "AI won't replace humans, but humans with AI will."; Author = "Karim Lakhani" }

    # Automation / Workflows
    @{ Text = "Automate the boring stuff."; Author = "Al Sweigart" }
    @{ Text = "The best code is no code at all."; Author = "Jeff Atwood" }
    @{ Text = "Don't repeat yourself."; Author = "Andy Hunt" }
    @{ Text = "Make it work, make it right, make it fast."; Author = "Kent Beck" }

    # Python / Data
    @{ Text = "Python is executable pseudocode."; Author = "Bruce Eckel" }
    @{ Text = "Data is the new oil."; Author = "Clive Humby" }
    @{ Text = "In God we trust. All others must bring data."; Author = "W. Edwards Deming" }
    @{ Text = "Premature optimization is the root of all evil."; Author = "Donald Knuth" }

    # Full-Stack / Web / JavaScript
    @{ Text = "Move fast and break things."; Author = "Mark Zuckerberg" }
    @{ Text = "Any application that can be written in JS, will be."; Author = "Jeff Atwood" }
    @{ Text = "The network is the computer."; Author = "John Gage" }
    @{ Text = "Software is eating the world."; Author = "Marc Andreessen" }

    # Engineering Principles
    @{ Text = "Talk is cheap. Show me the code."; Author = "Linus Torvalds" }
    @{ Text = "First, solve the problem. Then, write the code."; Author = "John Johnson" }
    @{ Text = "The only way to go fast is to go well."; Author = "Robert C. Martin" }
    @{ Text = "Good code is its own best documentation."; Author = "Steve McConnell" }
    @{ Text = "Simplicity is the ultimate sophistication."; Author = "Leonardo da Vinci" }
    @{ Text = "Complexity is the enemy of reliability."; Author = "Tony Hoare" }

    # Vision / Leadership
    @{ Text = "Stay hungry, stay foolish."; Author = "Steve Jobs" }
    @{ Text = "The best way to predict the future is to invent it."; Author = "Alan Kay" }
)


# 3. Pull latest remote changes to ensure local repo is synced
Push-Location $RepoPath
try {
    git checkout main --quiet
    git pull origin main --quiet
} catch {
    Write-Host "Warning: Could not pull latest changes from remote."
}
Pop-Location

# 4. Read current README content
$Content = [System.IO.File]::ReadAllText($ReadmePath)

# 4. Try to extract current quote to avoid duplicates
$CurrentText = ""
if ($Content -match 'text=([^&" >]+)') {
    $CurrentText = [uri]::UnescapeDataString($Matches[1])
}

# 5. Select a random quote (filtered to avoid current one unless forced or only 1 option)
$AvailableQuotes = $Quotes | Where-Object { $_.Text -ne $CurrentText }
if ($AvailableQuotes.Count -eq 0 -or $Force) {
    $AvailableQuotes = $Quotes
}

$SelectedQuote = $AvailableQuotes | Get-Random
$NewText = $SelectedQuote.Text
$NewAuthor = $SelectedQuote.Author

Write-Host "Selected New Quote: '$NewText' - $NewAuthor"

# 6. Reconstruct the capsule-render URL query params
$EncodedText = [uri]::EscapeDataString($NewText)
$EncodedAuthor = [uri]::EscapeDataString("- $NewAuthor")

# Calculate optimal fontSize based on character length to prevent text clipping
$Length = $NewText.Length
if ($Length -le 20) {
    $FontSize = 42
} elseif ($Length -le 25) {
    $FontSize = 36
} elseif ($Length -le 30) {
    $FontSize = 32
} elseif ($Length -le 35) {
    $FontSize = 28
} elseif ($Length -le 40) {
    $FontSize = 25
} elseif ($Length -le 45) {
    $FontSize = 23
} elseif ($Length -le 52) {
    $FontSize = 20
} else {
    $FontSize = 17
}

Write-Host "Quote length: $Length chars -> Calculated fontSize: $FontSize"

# Match the <img src="https://capsule-render.vercel.app/api?..."/> tag
# We replace text, fontSize, and desc parameters inside the img src
$Pattern = '(<img\s+src="https://capsule-render\.vercel\.app/api\?[^"]*?text=)[^&]+(.*?\bfontSize=)\d+(.*?\bdesc=)[^&]+'

if ($Content -match $Pattern) {
    # Replace text, fontSize, and desc inside the matched tag
    $NewContent = [regex]::Replace($Content, $Pattern, {
        param($m)
        $prefix = $m.Groups[1].Value
        $mid = $m.Groups[2].Value
        $suffix = $m.Groups[3].Value
        return "${prefix}${EncodedText}${mid}${FontSize}${suffix}${EncodedAuthor}"
    })
    
    # Write back to README.md (UTF-8 without BOM)
    $Utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($ReadmePath, $NewContent, $Utf8NoBom)
    Write-Host "Updated README.md locally with fitted fontSize=$FontSize."
} else {
    Write-Error "Could not find capsule-render image tag with 'text', 'fontSize', and 'desc' in README.md"
    exit 1
}

# 7. Push to GitHub
Write-Host "Pushing changes to GitHub using Git/GitHub CLI..."
Push-Location $RepoPath
try {
    # Verify we have git changes
    $status = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($status)) {
        Write-Host "No changes detected in README.md. Exiting."
        return
    }

    # Add, commit, and push
    git add README.md
    if ($LASTEXITCODE -ne 0) { throw "git add failed" }

    git commit -m "Update quote: $NewText"
    if ($LASTEXITCODE -ne 0) { throw "git commit failed" }

    # Use git push explicitly to main, which works from detached HEAD
    git push origin HEAD:main
    if ($LASTEXITCODE -ne 0) { throw "git push failed" }

    Write-Host "Successfully committed and pushed to GitHub!"
}
catch {
    Write-Error "Failed to commit and push changes: $_"
    exit 1
}
finally {
    Pop-Location
}