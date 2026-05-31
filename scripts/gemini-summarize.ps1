param (
    [Parameter(Mandatory=$true)]
    [string]$FilePath
)

if (-Not (Test-Path $FilePath)) {
    Write-Error "File not found: $FilePath"
    exit 1
}

$Content = Get-Content $FilePath -Raw
$Prompt = "Summarize the following content in 3 bullet points:`n`n$Content"

Write-Host "Running Gemini CLI to summarize $FilePath..."
gemini -p $Prompt -o text
