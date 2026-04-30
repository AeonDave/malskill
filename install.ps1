param(
    [string]$SourceRoot = "",
    [string]$Destination = "",
    [ValidateSet("folder", "skill", "zip", "")]
    [string]$Format = "",
    [ValidateSet("flat", "group", "")]
    [string]$Layout = "",
    [string[]]$SkillRefs = @(),
    [switch]$All
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    $SourceRoot = $ScriptDir
}
$SourceRoot = (Resolve-Path -LiteralPath $SourceRoot).Path

$ValidatorScript = Join-Path $ScriptDir "knowledge\skill-creator\scripts\quick_validate.py"
$PackagerScript = Join-Path $ScriptDir "knowledge\skill-creator\scripts\package_skill.py"
$DiscoveryExclusions = @(
    'dist',
    'installed-skills',
    'node_modules',
    '__pycache__'
)

function Write-Info([string]$Message) {
    Write-Host "[+] $Message" -ForegroundColor Green
}

function Write-Step([string]$Message) {
    Write-Host "[*] $Message" -ForegroundColor Cyan
}

function Write-Warn([string]$Message) {
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

function Normalize-SkillPath([string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return ""
    }

    return ($PathValue -replace '[\\/]+', '/').TrimEnd('/')
}

function Get-RelativePathNormalized([string]$BasePath, [string]$TargetPath) {
    return Normalize-SkillPath ([System.IO.Path]::GetRelativePath($BasePath, $TargetPath))
}

function Convert-NormalizedPathToSystemPath([string]$PathValue) {
    if ([string]::IsNullOrWhiteSpace($PathValue) -or $PathValue -eq '.') {
        return ""
    }

    return $PathValue.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
}

function Test-SkillDiscoveryExcluded([string]$RootPath, [string]$CandidatePath) {
    $relative = Get-RelativePathNormalized -BasePath $RootPath -TargetPath $CandidatePath
    if ([string]::IsNullOrWhiteSpace($relative) -or $relative -eq '.') {
        return $false
    }

    foreach ($segment in ($relative -split '/')) {
        if ($segment.StartsWith('.')) {
            return $true
        }
        if ($segment.StartsWith('_')) {
            return $true
        }
        if ($DiscoveryExclusions -icontains $segment) {
            return $true
        }
    }

    return $false
}

function Get-PythonInvocation {
    $venvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return @{ Exe = $venvPython; PrefixArgs = @() }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @{ Exe = $pythonCmd.Source; PrefixArgs = @() }
    }

    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @{ Exe = $pyCmd.Source; PrefixArgs = @('-3') }
    }

    throw "Python not found. Install Python or activate the repo virtual environment first."
}

try {
    $PythonInvocation = Get-PythonInvocation
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

function Invoke-PythonScript([string]$ScriptPath, [string[]]$ScriptArgs) {
    & $PythonInvocation.Exe @($PythonInvocation.PrefixArgs + @($ScriptPath) + $ScriptArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "Python script failed: $ScriptPath"
    }
}

function Get-SkillDirectories([string]$RootPath) {
    $skillFiles = Get-ChildItem -Path $RootPath -Recurse -File | Where-Object {
        $_.Name -ieq 'SKILL.md' -and -not (Test-SkillDiscoveryExcluded -RootPath $RootPath -CandidatePath $_.Directory.FullName)
    }
    if (-not $skillFiles) {
        throw "No SKILL.md files found under $RootPath"
    }

    $skills = foreach ($file in $skillFiles) {
        $dir = $file.Directory.FullName
        [pscustomobject]@{
            Name         = $file.Directory.Name
            RelativePath = Get-RelativePathNormalized -BasePath $RootPath -TargetPath $dir
            FullPath     = $dir
        }
    }

    return $skills | Sort-Object RelativePath, Name
}

function Parse-IndexSelection([string]$RawSelection, [int]$MaxIndex) {
    $trimmed = $RawSelection.Trim()
    if ([string]::IsNullOrWhiteSpace($trimmed)) {
        throw "Selection cannot be empty."
    }
    if ($trimmed -match '^(all|\*)$') {
        return 1..$MaxIndex
    }

    $result = New-Object System.Collections.Generic.List[int]
    foreach ($token in ($trimmed -split ',')) {
        $part = $token.Trim()
        if ($part -match '^(\d+)-(\d+)$') {
            $start = [int]$matches[1]
            $end = [int]$matches[2]
            if ($start -lt 1 -or $end -gt $MaxIndex -or $start -gt $end) {
                throw "Invalid range: $part"
            }
            foreach ($value in $start..$end) {
                $result.Add($value)
            }
            continue
        }

        if ($part -match '^\d+$') {
            $value = [int]$part
            if ($value -lt 1 -or $value -gt $MaxIndex) {
                throw "Index out of range: $part"
            }
            $result.Add($value)
            continue
        }

        throw "Invalid selection token: $part"
    }

    return $result | Sort-Object -Unique
}

function Resolve-SkillReferences([object[]]$Skills, [string[]]$References) {
    $resolved = New-Object System.Collections.Generic.List[object]

    foreach ($reference in $References) {
        $needle = Normalize-SkillPath $reference.Trim()
        if ([string]::IsNullOrWhiteSpace($needle)) {
            continue
        }

        $matches = @(
            $Skills | Where-Object {
                (Normalize-SkillPath $_.RelativePath) -ieq $needle -or
                (Normalize-SkillPath $_.FullPath) -ieq $needle -or
                $_.Name -ieq $needle
            }
        )

        if ($matches.Count -eq 0) {
            throw "Skill reference not found: $reference"
        }

        if ($matches.Count -gt 1 -and -not ($matches | Where-Object { (Normalize-SkillPath $_.RelativePath) -ieq $needle -or (Normalize-SkillPath $_.FullPath) -ieq $needle })) {
            $choices = ($matches | ForEach-Object { $_.RelativePath }) -join ', '
            throw "Ambiguous skill reference '$reference'. Use one of: $choices"
        }

        if (($matches | Where-Object { (Normalize-SkillPath $_.RelativePath) -ieq $needle -or (Normalize-SkillPath $_.FullPath) -ieq $needle }).Count -gt 0) {
            $matches = @($matches | Where-Object { (Normalize-SkillPath $_.RelativePath) -ieq $needle -or (Normalize-SkillPath $_.FullPath) -ieq $needle })
        }

        foreach ($match in $matches) {
            if (-not ($resolved | Where-Object { $_.FullPath -eq $match.FullPath })) {
                $resolved.Add($match)
            }
        }
    }

    return $resolved.ToArray() | Sort-Object RelativePath
}

function Select-Skills([object[]]$Skills) {
    if ($All) {
        return $Skills
    }

    if ($SkillRefs.Count -gt 0) {
        return Resolve-SkillReferences -Skills $Skills -References $SkillRefs
    }

    Write-Step "Discovered $($Skills.Count) skill folders under $SourceRoot"
    for ($i = 0; $i -lt $Skills.Count; $i++) {
        $index = $i + 1
        Write-Host ("[{0,3}] {1}" -f $index, $Skills[$i].RelativePath) -ForegroundColor Cyan
    }
    Write-Host ""
    $rawSelection = Read-Host "Select skills by index (e.g. 1,4-7 or all)"
    $indexes = Parse-IndexSelection -RawSelection $rawSelection -MaxIndex $Skills.Count

    $selected = foreach ($index in $indexes) {
        $Skills[$index - 1]
    }

    return $selected
}

function Select-Destination {
    if (-not [string]::IsNullOrWhiteSpace($Destination)) {
        return [System.IO.Path]::GetFullPath($Destination)
    }

    $homeDir = [Environment]::GetFolderPath('UserProfile')
    $knownOptions = New-Object System.Collections.Generic.List[string]
    foreach ($path in @(
        (Join-Path $homeDir '.agents\skills'),
        (Join-Path $homeDir '.claude\skills'),
        (Join-Path $homeDir '.copilot\skills')
    )) {
        $resolved = [System.IO.Path]::GetFullPath($path)
        if ((Test-Path -LiteralPath $resolved) -and -not $knownOptions.Contains($resolved)) {
            $knownOptions.Add($resolved)
        }
    }

    if (-not $IsWindows) {
        foreach ($path in @('/etc/codex/skills')) {
            if ((Test-Path -LiteralPath $path) -and -not $knownOptions.Contains($path)) {
                $knownOptions.Add($path)
            }
        }
    }

    $options = @(
        $knownOptions | ForEach-Object {
            [pscustomobject]@{
                Path   = $_
                Exists = $true
            }
        }
    )

    Write-Step "Choose destination root"
    for ($i = 0; $i -lt $options.Count; $i++) {
        Write-Host ("[{0}] {1} (existing)" -f ($i + 1), $options[$i].Path) -ForegroundColor Cyan
    }
    Write-Host ("[{0}] Enter a custom destination path" -f ($options.Count + 1)) -ForegroundColor Cyan

    $choice = Read-Host "Select destination"

    $selectedIndex = 0
    if (-not [int]::TryParse($choice.Trim(), [ref]$selectedIndex)) {
        throw "Invalid destination selection: $choice"
    }

    if ($selectedIndex -ge 1 -and $selectedIndex -le $options.Count) {
        return $options[$selectedIndex - 1].Path
    }

    if ($selectedIndex -eq ($options.Count + 1)) {
            $manual = Read-Host "Enter destination path"
            if ([string]::IsNullOrWhiteSpace($manual)) {
                throw "Destination path cannot be empty."
            }
            return [System.IO.Path]::GetFullPath($manual)
    }

    throw "Invalid destination selection: $choice"
}

function Select-Format {
    if (-not [string]::IsNullOrWhiteSpace($Format)) {
        return $Format
    }

    Write-Step "Choose output format"
    Write-Host "[1] folder  - copy each skill directory into the destination root" -ForegroundColor Cyan
    Write-Host "[2] .skill  - create a standard zip-based .skill archive per selected skill" -ForegroundColor Cyan
    Write-Host "[3] .zip    - create a standard .zip archive per selected skill" -ForegroundColor Cyan
    $choice = Read-Host "Select format"
    switch ($choice.Trim()) {
        '1' { return 'folder' }
        '2' { return 'skill' }
        '3' { return 'zip' }
        default { throw "Invalid format selection: $choice" }
    }
}

function Select-Layout {
    if (-not [string]::IsNullOrWhiteSpace($Layout)) {
        return $Layout
    }

    Write-Step "Choose install layout"
    Write-Host "[1] flat   - install every selected skill at the destination root" -ForegroundColor Cyan
    Write-Host "[2] group  - preserve the source-root-relative category structure" -ForegroundColor Cyan
    $choice = Read-Host "Select layout"
    switch ($choice.Trim()) {
        '1' { return 'flat' }
        '2' { return 'group' }
        default { throw "Invalid layout selection: $choice" }
    }
}

function Assert-UniqueArtifactNames([object[]]$SelectedSkills, [string]$LayoutChoice) {
    if ($LayoutChoice -eq 'group') {
        return
    }

    $duplicates = $SelectedSkills | Group-Object Name | Where-Object { $_.Count -gt 1 }
    if ($duplicates) {
        $details = foreach ($duplicate in $duplicates) {
            $paths = ($duplicate.Group | ForEach-Object { $_.RelativePath }) -join ', '
            "- $($duplicate.Name): $paths"
        }
        throw "Selected skills would collide at install time:`n$($details -join "`n")"
    }
}

function Get-InstallFolderTarget([string]$DestinationRoot, [object]$Skill, [string]$LayoutChoice) {
    if ($LayoutChoice -eq 'group' -and $Skill.RelativePath -ne '.') {
        $relativePath = Convert-NormalizedPathToSystemPath $Skill.RelativePath
        return [System.IO.Path]::Combine($DestinationRoot, $relativePath)
    }

    return [System.IO.Path]::Combine($DestinationRoot, $Skill.Name)
}

function Get-InstallArchiveTarget([string]$DestinationRoot, [object]$Skill, [string]$LayoutChoice, [string]$Extension) {
    $fileName = "{0}.{1}" -f $Skill.Name, $Extension
    if ($LayoutChoice -eq 'group' -and $Skill.RelativePath -ne '.') {
        $relativePath = Convert-NormalizedPathToSystemPath $Skill.RelativePath
        $relativeDir = Split-Path -Path $relativePath -Parent
        if (-not [string]::IsNullOrWhiteSpace($relativeDir)) {
            return [System.IO.Path]::Combine($DestinationRoot, $relativeDir, $fileName)
        }
    }

    return [System.IO.Path]::Combine($DestinationRoot, $fileName)
}

function Validate-SelectedSkills([object[]]$SelectedSkills) {
    foreach ($skill in $SelectedSkills) {
        Write-Step "Validating $($skill.RelativePath)"
        Invoke-PythonScript -ScriptPath $ValidatorScript -ScriptArgs @($skill.FullPath)
    }
}

function Remove-ExistingSkillDirectory([string]$TargetPath) {
    if (-not (Test-Path -LiteralPath $TargetPath)) {
        return
    }

    $item = Get-Item -LiteralPath $TargetPath
    if (-not $item.PSIsContainer) {
        throw "Target exists and is not a directory: $TargetPath"
    }

    Remove-Item -LiteralPath $TargetPath -Recurse -Force
}

function Install-AsFolders([object[]]$SelectedSkills, [string]$DestinationRoot, [string]$LayoutChoice) {
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null

    foreach ($skill in $SelectedSkills) {
        $targetDir = Get-InstallFolderTarget -DestinationRoot $DestinationRoot -Skill $skill -LayoutChoice $LayoutChoice
        $targetParent = Split-Path -Path $targetDir -Parent
        if (Test-Path -LiteralPath $targetDir) {
            Write-Warn "Removing existing installed skill directory: $targetDir"
            Remove-ExistingSkillDirectory -TargetPath $targetDir
        }

        if (-not [string]::IsNullOrWhiteSpace($targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }

        Write-Step "Installing folder $($skill.RelativePath) -> $targetDir"
        Copy-Item -LiteralPath $skill.FullPath -Destination $targetDir -Recurse -Force
    }
}

function Install-AsArchives([object[]]$SelectedSkills, [string]$DestinationRoot, [string]$LayoutChoice, [string]$Extension) {
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null

    foreach ($skill in $SelectedSkills) {
        $targetFile = Get-InstallArchiveTarget -DestinationRoot $DestinationRoot -Skill $skill -LayoutChoice $LayoutChoice -Extension $Extension
        $targetParent = Split-Path -Path $targetFile -Parent
        if (-not [string]::IsNullOrWhiteSpace($targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }

        if (Test-Path -LiteralPath $targetFile) {
            $item = Get-Item -LiteralPath $targetFile
            if ($item.PSIsContainer) {
                throw "Refusing to overwrite directory with .$Extension archive: $targetFile"
            }
            Write-Warn "Removing existing archive: $targetFile"
            Remove-Item -LiteralPath $targetFile -Force
        }

        Write-Step "Packaging $($skill.RelativePath) -> $targetFile"
        if ($Extension -eq 'skill') {
            Invoke-PythonScript -ScriptPath $PackagerScript -ScriptArgs @($skill.FullPath, $targetParent)
            continue
        }

        $tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid().ToString())
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        try {
            Invoke-PythonScript -ScriptPath $PackagerScript -ScriptArgs @($skill.FullPath, $tempDir)
            $generatedArchive = Join-Path $tempDir ("{0}.skill" -f $skill.Name)
            if (-not (Test-Path -LiteralPath $generatedArchive)) {
                throw "Packager did not create expected archive: $generatedArchive"
            }

            Move-Item -LiteralPath $generatedArchive -Destination $targetFile -Force
        }
        finally {
            if (Test-Path -LiteralPath $tempDir) {
                Remove-Item -LiteralPath $tempDir -Recurse -Force
            }
        }
    }
}

try {
    Write-Host ""
    Write-Host "Agent Skills installer" -ForegroundColor Green
    Write-Host "Source root: $SourceRoot" -ForegroundColor DarkGray
    Write-Host ""

    $skills = Get-SkillDirectories -RootPath $SourceRoot
    $selectedSkills = @(Select-Skills -Skills $skills)
    if ($selectedSkills.Count -eq 0) {
        throw "No skills selected."
    }

    $resolvedFormat = Select-Format
    $resolvedLayout = Select-Layout
    Assert-UniqueArtifactNames -SelectedSkills $selectedSkills -LayoutChoice $resolvedLayout
    $destinationRoot = Select-Destination

    Write-Host ""
    Write-Info "Selected $($selectedSkills.Count) skill(s)"
    Write-Info "Destination root: $destinationRoot"
    Write-Info "Format: $resolvedFormat"
    Write-Info "Layout: $resolvedLayout"
    Write-Host ""

    Validate-SelectedSkills -SelectedSkills $selectedSkills

    switch ($resolvedFormat) {
        'folder' { Install-AsFolders -SelectedSkills $selectedSkills -DestinationRoot $destinationRoot -LayoutChoice $resolvedLayout }
        'skill'  { Install-AsArchives -SelectedSkills $selectedSkills -DestinationRoot $destinationRoot -LayoutChoice $resolvedLayout -Extension 'skill' }
        'zip'    { Install-AsArchives -SelectedSkills $selectedSkills -DestinationRoot $destinationRoot -LayoutChoice $resolvedLayout -Extension 'zip' }
        default  { throw "Unsupported format: $resolvedFormat" }
    }

    Write-Host ""
    Write-Info "Install complete."
    foreach ($skill in $selectedSkills) {
        if ($resolvedFormat -eq 'folder') {
            Write-Host ("    {0}" -f (Get-InstallFolderTarget -DestinationRoot $destinationRoot -Skill $skill -LayoutChoice $resolvedLayout)) -ForegroundColor DarkGray
        } elseif ($resolvedFormat -eq 'zip') {
            Write-Host ("    {0}" -f (Get-InstallArchiveTarget -DestinationRoot $destinationRoot -Skill $skill -LayoutChoice $resolvedLayout -Extension 'zip')) -ForegroundColor DarkGray
        } else {
            Write-Host ("    {0}" -f (Get-InstallArchiveTarget -DestinationRoot $destinationRoot -Skill $skill -LayoutChoice $resolvedLayout -Extension 'skill')) -ForegroundColor DarkGray
        }
    }
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
