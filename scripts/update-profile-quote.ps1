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

# 2. Curated list of quotes (keep them relatively concise for capsule-render)
$Quotes = @(
    @{ Text = "Talk is cheap. Show me the code."; Author = "Linus Torvalds" }
    @{ Text = "Stay hungry, stay foolish."; Author = "Steve Jobs" }
    @{ Text = "Make it simple, but significant."; Author = "Don Draper" }
    @{ Text = "Simplicity is the soul of efficiency."; Author = "Austin Freeman" }
    @{ Text = "Simplicity is the key to brilliance."; Author = "Bruce Lee" }
    @{ Text = "Strive for simplicity."; Author = "Unknown" }
    @{ Text = "Move fast and break things."; Author = "Mark Zuckerberg" }
    @{ Text = "Keep it simple, stupid."; Author = "Kelly Johnson" }
    @{ Text = "Less is more."; Author = "Ludwig Mies" }
    @{ Text = "Think different."; Author = "Apple" }
    @{ Text = "Code is poetry."; Author = "WordPress" }
    @{ Text = "Don't repeat yourself."; Author = "Andy Hunt" }
    @{ Text = "Fail fast, learn faster."; Author = "Unknown" }
    @{ Text = "Done is better than perfect."; Author = "Sheryl Sandberg" }
    @{ Text = "Automate everything."; Author = "Unknown" }
    @{ Text = "Build, measure, learn."; Author = "Eric Ries" }
    @{ Text = "To iterate is human, to recurse divine."; Author = "L. Peter Deutsch" }
    @{ Text = "Focus on impact."; Author = "Mark Zuckerberg" }
    @{ Text = "One man's constant is another's variable."; Author = "Alan Perlis" }
    @{ Text = "Logic is the beginning of wisdom."; Author = "Spock" }
    @{ Text = "Be yourself; everyone else is taken."; Author = "Oscar Wilde" }
    @{ Text = "Make it work, make it right, make it fast."; Author = "Kent Beck" }
    @{ Text = "Simplicity is prerequisite for reliability."; Author = "Edsger W. Dijkstra" }
)

# 3. Read current README content
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

# Match the <img src="https://capsule-render.vercel.app/api?..."/> tag
# We replace the text and desc parameters inside the img src
$Pattern = '(<img\s+src="https://capsule-render\.vercel\.app/api\?[^"]*?text=)([^&]+)([^"]*?desc=)([^&]+)([^"]*"[^>]*>)'

if ($Content -match $Pattern) {
    # Replace text and desc inside the matched tag
    $NewContent = [regex]::Replace($Content, $Pattern, {
        param($m)
        $prefix = $m.Groups[1].Value
        $suffix1 = $m.Groups[3].Value
        $suffix2 = $m.Groups[5].Value
        return "${prefix}${EncodedText}${suffix1}${EncodedAuthor}${suffix2}"
    })
    
    # Write back to README.md (UTF-8 without BOM)
    $Utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($ReadmePath, $NewContent, $Utf8NoBom)
    Write-Host "Updated README.md locally."
} else {
    Write-Error "Could not find capsule-render image tag with 'text' and 'desc' in README.md"
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

    # Use git push, which inherits GitHub CLI credentials
    git push
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
