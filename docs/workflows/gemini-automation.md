# Gemini CLI Workflow Automation (Day 9)

## Overview
For Day 9 of the 30-Day AI CLI Experimentation Plan, we've created a simple repetitive task automation script utilizing the Gemini CLI's headless mode (`-p` flag).

## The Task
Summarizing markdown or text files is a common repetitive task. We created a PowerShell script `scripts/gemini-summarize.ps1` that takes a file path as input, reads the content, and asks Gemini to summarize it in 3 bullet points.

## The Script
Located at `scripts/gemini-summarize.ps1`:

```powershell
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
```

## Usage
Run the script from the repository root:
```powershell
.\scripts\gemini-summarize.ps1 -FilePath "docs\workflow-audit.md"
```

This effectively demonstrates how the Gemini CLI can be integrated into native shell scripts to automate AI-driven data processing.
