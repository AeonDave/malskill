param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Script,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Convert-ToWslPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WindowsPath
    )

    $result = & wsl.exe -e sh -lc 'wslpath -a "$1"' sh $WindowsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to convert path to WSL format: $WindowsPath"
    }

    return ($result | Select-Object -First 1).Trim()
}

function Convert-ArgumentIfPathLike {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value,
        [Parameter(Mandatory = $true)]
        [string]$BaseDirectory
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Value
    }

    $candidate = $Value
    $looksAbsoluteWindows = $candidate -match '^[A-Za-z]:[\\/]'
    $relativePath = Join-Path $BaseDirectory $candidate

    if ($looksAbsoluteWindows -and (Test-Path -LiteralPath $candidate)) {
        return Convert-ToWslPath -WindowsPath (Resolve-Path -LiteralPath $candidate).Path
    }

    if (-not $looksAbsoluteWindows -and (Test-Path -LiteralPath $relativePath)) {
        return Convert-ToWslPath -WindowsPath (Resolve-Path -LiteralPath $relativePath).Path
    }

    return $Value
}

function Convert-ToShellLiteral {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $replacement = "'" + '"' + "'" + '"' + "'"
    return "'" + $Value.Replace("'", $replacement) + "'"
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
    throw 'WSL is not available on this machine. Install WSL or use the Python helpers instead.'
}

$currentDirectory = (Get-Location).Path
$scriptPath = if ([System.IO.Path]::IsPathRooted($Script)) {
    $Script
} else {
    Join-Path $PSScriptRoot $Script
}

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Shell script not found: $scriptPath"
}

$linuxCwd = Convert-ToWslPath -WindowsPath $currentDirectory
$linuxScript = Convert-ToWslPath -WindowsPath (Resolve-Path -LiteralPath $scriptPath).Path
$linuxArgs = foreach ($arg in $ScriptArgs) {
    Convert-ArgumentIfPathLike -Value $arg -BaseDirectory $currentDirectory
}

$quotedParts = @(
    "cd $(Convert-ToShellLiteral -Value $linuxCwd)",
    '&&',
    (Convert-ToShellLiteral -Value $linuxScript)
)
foreach ($arg in $linuxArgs) {
    $quotedParts += Convert-ToShellLiteral -Value $arg
}
$commandText = ($quotedParts -join ' ')

& wsl.exe -e sh -lc $commandText
exit $LASTEXITCODE