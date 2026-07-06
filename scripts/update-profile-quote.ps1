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
    @{ Text = "AI Is The New Electricity"; Author = "Andrew Ng" }
    @{ Text = "First, solve the problem. Then, write the code."; Author = "John Johnson" }
    @{ Text = "Simplicity is the ultimate sophistication."; Author = "Leonardo da Vinci" }
    @{ Text = "The best way to predict the future is to invent it."; Author = "Alan Kay" }
    @{ Text = "Computers are useless. They can only give you answers."; Author = "Pablo Picasso" }
    @{ Text = "Stay hungry, stay foolish."; Author = "Steve Jobs" }
    @{ Text = "First do it, then do it right, then do it fast."; Author = "Kent Beck" }
    @{ Text = "Make it simple, but significant."; Author = "Don Draper" }
    @{ Text = "If you're not failing, you're not innovating."; Author = "Elon Musk" }
    @{ Text = "The code you delete makes you a good programmer."; Author = "Mario Fusco" }
    @{ Text = "One of my most productive days was throwing away 1000 lines of code."; Author = "Ken Thompson" }
    @{ Text = "The only way to do great work is to love what you do."; Author = "Steve Jobs" }
    @{ Text = "Quality is not an act, it is a habit."; Author = "Aristotle" }
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
