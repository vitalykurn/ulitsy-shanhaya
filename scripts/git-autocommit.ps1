<#
.SYNOPSIS
    Auto-commit current git changes for this repository.

.DESCRIPTION
    Adds all changes, creates a commit, and optionally pushes to remote.
    Intended to be used from an IDE task.

.PARAMETER Message
    Commit message. If omitted, a default message is generated.

.PARAMETER Push
    Push to remote after successful commit. If upstream is missing, sets it.

.PARAMETER DryRun
    Show what would be committed without creating a commit.

.EXAMPLE
    .\scripts\git-autocommit.ps1

.EXAMPLE
    .\scripts\git-autocommit.ps1 -Message "chore: sync local changes" -Push

.EXAMPLE
    .\scripts\git-autocommit.ps1 -DryRun
#>
param(
    [string]$Message = "",
    [switch]$Push,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Assert-GitInstalled {
    if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
        throw "git is not installed or not available in PATH."
    }
}

function Get-RepositoryRoot {
    param([string]$ScriptPath)
    return Split-Path -Parent (Split-Path -Parent $ScriptPath)
}

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        # Git writes errors to stderr; avoid NativeCommandError noise in PowerShell.
        $output = & git.exe @GitArgs 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                $_.ToString()
            } else {
                $_
            }
        }
        return @{
            ExitCode = $LASTEXITCODE
            Output   = @($output)
        }
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Push-CurrentBranch {
    $head = Invoke-Git rev-parse --abbrev-ref HEAD
    if ($head.ExitCode -ne 0) {
        throw "Failed to resolve current branch."
    }
    $branch = ($head.Output | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($branch)) {
        throw "Failed to resolve current branch."
    }

    $upstream = Invoke-Git rev-parse --abbrev-ref --symbolic-full-name "@{u}"
    $hasUpstream = ($upstream.ExitCode -eq 0) -and -not [string]::IsNullOrWhiteSpace(($upstream.Output | Out-String).Trim())

    if (-not $hasUpstream) {
        Write-Host "No upstream configured. Pushing with -u origin $branch ..."
        $push = Invoke-Git push -u origin $branch
    } else {
        $push = Invoke-Git push
    }

    if ($push.ExitCode -ne 0) {
        $detail = ($push.Output | Out-String).Trim()
        if ($detail) {
            Write-Host $detail
        }
        throw "git push failed."
    }
}

Assert-GitInstalled

$RepoRoot = Get-RepositoryRoot -ScriptPath $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

if (-not (Test-Path (Join-Path $RepoRoot ".git"))) {
    throw "Repository root not found at: $RepoRoot"
}

$status = @(git status --porcelain)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read git status."
}

if ($status.Count -eq 0) {
    Write-Host "No changes to commit."
    if ($Push) {
        Write-Host "Push requested. Pushing current branch..."
        Push-CurrentBranch
    }
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "chore: auto-commit $($status.Count) changed file(s)"
}

if ($DryRun) {
    Write-Host "Dry run mode: no git changes will be written."
    Write-Host "Repository: $RepoRoot"
    Write-Host "Commit message: $Message"
    Write-Host "Files to commit:"
    foreach ($line in $status) {
        Write-Host "  $line"
    }
    if ($Push) {
        Write-Host "Push: enabled"
    } else {
        Write-Host "Push: disabled"
    }
    exit 0
}

git add -A
if ($LASTEXITCODE -ne 0) {
    throw "git add failed."
}

git commit -m "$Message"
if ($LASTEXITCODE -ne 0) {
    throw "git commit failed."
}

if ($Push) {
    Push-CurrentBranch
}

Write-Host "Auto-commit completed."
