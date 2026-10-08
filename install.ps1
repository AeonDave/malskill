#requires -Version 7.0

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

$ValidatorScript = Join-Path $ScriptDir "scripts\quick_validate.py"
$BatchValidatorScript = Join-Path $ScriptDir "scripts\validate_all.py"
$PackagerScript = Join-Path $ScriptDir "scripts\package_skill.py"
$SelectorScript = Join-Path $ScriptDir "scripts\skill_selector.py"
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

# ─── Skills discovery ────────────────────────────────────────────────────────

function Get-SkillDirectories([string]$RootPath) {
    $skillFiles = Get-ChildItem -LiteralPath $RootPath -Recurse -File | Where-Object {
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

function Resolve-SkillReferences([object[]]$Skills, [string[]]$References) {
    $resolved = New-Object System.Collections.Generic.List[object]

    foreach ($reference in $References) {
        $needle = Normalize-SkillPath $reference.Trim()
        if ([string]::IsNullOrWhiteSpace($needle)) {
            continue
        }

        $matchedSkills = @(
            $Skills | Where-Object {
                (Normalize-SkillPath $_.RelativePath) -ieq $needle -or
                (Normalize-SkillPath $_.FullPath) -ieq $needle -or
                $_.Name -ieq $needle
            }
        )

        if ($matchedSkills.Count -eq 0) {
            throw "Skill reference not found: $reference"
        }

        if ($matchedSkills.Count -gt 1 -and -not ($matchedSkills | Where-Object { (Normalize-SkillPath $_.RelativePath) -ieq $needle -or (Normalize-SkillPath $_.FullPath) -ieq $needle })) {
            $choices = ($matchedSkills | ForEach-Object { $_.RelativePath }) -join ', '
            throw "Ambiguous skill reference '$reference'. Use one of: $choices"
        }

        if (($matchedSkills | Where-Object { (Normalize-SkillPath $_.RelativePath) -ieq $needle -or (Normalize-SkillPath $_.FullPath) -ieq $needle }).Count -gt 0) {
            $matchedSkills = @($matchedSkills | Where-Object { (Normalize-SkillPath $_.RelativePath) -ieq $needle -or (Normalize-SkillPath $_.FullPath) -ieq $needle })
        }

        foreach ($match in $matchedSkills) {
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
    $skillsFile = [System.IO.Path]::GetTempFileName()
    try {
        $selectorSkills = @($Skills | ForEach-Object {
            @{ name = $_.Name; path = (Normalize-SkillPath $_.RelativePath) }
        })
        $json = ConvertTo-Json -InputObject $selectorSkills -Depth 3
        [System.IO.File]::WriteAllText($skillsFile, $json, [System.Text.UTF8Encoding]::new($false))
        $selectedPaths = @(& $PythonInvocation.Exe @($PythonInvocation.PrefixArgs + @($SelectorScript, '--skills-file', $skillsFile)))
        if ($LASTEXITCODE -ne 0) {
            throw "Skill selection cancelled or failed."
        }

        $byPath = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::Ordinal)
        foreach ($skill in $Skills) {
            $byPath.Add((Normalize-SkillPath $skill.RelativePath), $skill)
        }
        $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
        foreach ($path in $selectedPaths) {
            if (-not $byPath.ContainsKey($path)) {
                throw "Selector returned an unknown skill path: $path"
            }
            if ($seen.Add($path)) {
                $byPath[$path]
            }
        }
    }
    finally {
        if (Test-Path -LiteralPath $skillsFile) {
            Remove-Item -LiteralPath $skillsFile -Force
        }
    }
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
    $artifacts = foreach ($skill in $SelectedSkills) {
        $stem = $skill.Name
        if ($LayoutChoice -eq 'group' -and $skill.RelativePath -ne '.') {
            $stem = Normalize-SkillPath $skill.RelativePath
        }
        [pscustomobject]@{ Stem = $stem; Skill = $skill }
    }
    $duplicates = $artifacts | Group-Object Stem | Where-Object { $_.Count -gt 1 }
    if ($duplicates) {
        $details = foreach ($duplicate in $duplicates) {
            $paths = ($duplicate.Group | ForEach-Object { $_.Skill.RelativePath }) -join ', '
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
    if (-not $SelectedSkills -or $SelectedSkills.Count -eq 0) {
        return
    }

    Write-Step ("Validating {0} skill(s) in a single Python process" -f $SelectedSkills.Count)
    $batchArgs = New-Object System.Collections.Generic.List[string]
    foreach ($skill in $SelectedSkills) {
        $batchArgs.Add('--skill-dir')
        $batchArgs.Add($skill.FullPath)
    }
    Invoke-PythonScript -ScriptPath $BatchValidatorScript -ScriptArgs $batchArgs.ToArray()
}

function Get-AbsoluteInstallPath([string]$PathValue) {
    $absolute = [System.IO.Path]::GetFullPath($PathValue)
    $root = [System.IO.Path]::GetPathRoot($absolute)
    if ($absolute -eq $root) {
        return $root
    }
    return $absolute.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
}

function Test-InstallPathContains([string]$ParentPath, [string]$ChildPath) {
    $parent = Get-AbsoluteInstallPath $ParentPath
    $child = Get-AbsoluteInstallPath $ChildPath
    $comparison = [System.StringComparison]::Ordinal
    if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) {
        $comparison = [System.StringComparison]::OrdinalIgnoreCase
    }
    $prefix = $parent.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    return $child.Equals($parent, $comparison) -or $child.StartsWith($prefix, $comparison)
}

function Assert-NoInstallReparsePoints([string]$PathValue, [System.Collections.Generic.HashSet[string]]$CheckedPaths = $null) {
    $current = Get-AbsoluteInstallPath $PathValue
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        if ($null -ne $CheckedPaths -and $CheckedPaths.Contains($current)) {
            break
        }
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Refusing an install path through a symbolic link or junction: $current"
            }
        }
        if ($null -ne $CheckedPaths) {
            [void]$CheckedPaths.Add($current)
        }
        $current = [System.IO.Path]::GetDirectoryName($current)
    }
}

function Assert-InstallTargetWithinRoot([string]$TargetPath, [string]$DestinationRoot, [System.Collections.Generic.HashSet[string]]$CheckedPaths = $null) {
    $target = Get-AbsoluteInstallPath $TargetPath
    $destinationPath = Get-AbsoluteInstallPath $DestinationRoot
    if ($target -eq $destinationPath -or -not (Test-InstallPathContains -ParentPath $destinationPath -ChildPath $target)) {
        throw "Install target must be inside the destination root: $target"
    }
    Assert-NoInstallReparsePoints -PathValue $target -CheckedPaths $CheckedPaths
}

function New-InstallSourcePathIndex([object[]]$SourceSkills) {
    $comparer = [System.StringComparer]::Ordinal
    if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) {
        $comparer = [System.StringComparer]::OrdinalIgnoreCase
    }
    $sourcePaths = [System.Collections.Generic.HashSet[string]]::new($comparer)
    $ancestorPaths = [System.Collections.Generic.HashSet[string]]::new($comparer)
    $protectedPaths = [System.Collections.Generic.List[string]]::new()
    $protectedPaths.Add((Get-AbsoluteInstallPath $SourceRoot))
    foreach ($sourceSkill in $SourceSkills) {
        $sourcePath = Get-AbsoluteInstallPath $sourceSkill.FullPath
        [void]$sourcePaths.Add($sourcePath)
        $protectedPaths.Add($sourcePath)
    }
    foreach ($path in $protectedPaths) {
        $current = $path
        while (-not [string]::IsNullOrWhiteSpace($current)) {
            if (-not $ancestorPaths.Add($current)) {
                break
            }
            $current = [System.IO.Path]::GetDirectoryName($current)
        }
    }
    return @{ Paths = $sourcePaths; Ancestors = $ancestorPaths }
}

function Assert-InstallSourceSeparation([string]$TargetPath, [object[]]$SourceSkills, [object]$SourcePathIndex = $null) {
    # Protect all sources, including unselected skills, without comparing every pair.
    if ($null -eq $SourcePathIndex) {
        $SourcePathIndex = New-InstallSourcePathIndex $SourceSkills
    }
    $target = Get-AbsoluteInstallPath $TargetPath
    if ($SourcePathIndex.Ancestors.Contains($target)) {
        throw "Install target overlaps a source path: $TargetPath"
    }
    $current = $target
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        if ($SourcePathIndex.Paths.Contains($current)) {
            throw "Install target overlaps a source skill: $TargetPath ($current)"
        }
        $current = [System.IO.Path]::GetDirectoryName($current)
    }
}

function Assert-SafeInstallTargets([object[]]$SelectedSkills, [object[]]$SourceSkills, [string]$DestinationRoot, [string]$LayoutChoice, [string]$FormatChoice) {
    $sourcePathIndex = New-InstallSourcePathIndex $SourceSkills
    # This cache exists only during preflight; writes and deletion recheck the target.
    $checkedPaths = [System.Collections.Generic.HashSet[string]]::new($sourcePathIndex.Paths.Comparer)
    Assert-NoInstallReparsePoints -PathValue $SourceRoot -CheckedPaths $checkedPaths
    foreach ($sourceSkill in $SourceSkills) {
        Assert-NoInstallReparsePoints -PathValue $sourceSkill.FullPath -CheckedPaths $checkedPaths
    }
    foreach ($skill in $SelectedSkills) {
        if ($FormatChoice -eq 'folder') {
            $target = Get-InstallFolderTarget -DestinationRoot $DestinationRoot -Skill $skill -LayoutChoice $LayoutChoice
        } else {
            $target = Get-InstallArchiveTarget -DestinationRoot $DestinationRoot -Skill $skill -LayoutChoice $LayoutChoice -Extension $FormatChoice
        }
        Assert-InstallTargetWithinRoot -TargetPath $target -DestinationRoot $DestinationRoot -CheckedPaths $checkedPaths
        Assert-InstallSourceSeparation -TargetPath $target -SourceSkills $SourceSkills -SourcePathIndex $sourcePathIndex
    }
}

function Remove-ExistingSkillDirectory([string]$TargetPath, [string]$DestinationRoot, [object[]]$SourceSkills, [object]$SourcePathIndex = $null) {
    Assert-InstallTargetWithinRoot -TargetPath $TargetPath -DestinationRoot $DestinationRoot
    Assert-InstallSourceSeparation -TargetPath $TargetPath -SourceSkills $SourceSkills -SourcePathIndex $SourcePathIndex
    if (-not (Test-Path -LiteralPath $TargetPath)) {
        return
    }

    $item = Get-Item -LiteralPath $TargetPath
    if (-not $item.PSIsContainer) {
        throw "Target exists and is not a directory: $TargetPath"
    }

    Remove-Item -LiteralPath $TargetPath -Recurse -Force
}

function Install-AsFolders([object[]]$SelectedSkills, [object[]]$SourceSkills, [string]$DestinationRoot, [string]$LayoutChoice) {
    New-Item -ItemType Directory -Path $DestinationRoot -Force | Out-Null
    $sourcePathIndex = New-InstallSourcePathIndex $SourceSkills

    foreach ($skill in $SelectedSkills) {
        $targetDir = Get-InstallFolderTarget -DestinationRoot $DestinationRoot -Skill $skill -LayoutChoice $LayoutChoice
        Assert-InstallTargetWithinRoot -TargetPath $targetDir -DestinationRoot $DestinationRoot
        $targetParent = Split-Path -Path $targetDir -Parent
        if (Test-Path -LiteralPath $targetDir) {
            Write-Warn "Removing existing installed skill directory: $targetDir"
            Remove-ExistingSkillDirectory -TargetPath $targetDir -DestinationRoot $DestinationRoot -SourceSkills $SourceSkills -SourcePathIndex $sourcePathIndex
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
        Assert-InstallTargetWithinRoot -TargetPath $targetFile -DestinationRoot $DestinationRoot
        $targetParent = Split-Path -Path $targetFile -Parent
        if (-not [string]::IsNullOrWhiteSpace($targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }

        if (Test-Path -LiteralPath $targetFile) {
            $item = Get-Item -LiteralPath $targetFile
            if ($item.PSIsContainer) {
                throw "Refusing to overwrite directory with .$Extension archive: $targetFile"
            }
            Write-Warn "Replacing existing archive: $targetFile"
        }

        Write-Step "Packaging $($skill.RelativePath) -> $targetFile"
        $tempRoot = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
        $tempDir = Join-Path $tempRoot ([System.Guid]::NewGuid().ToString())
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
                Assert-InstallTargetWithinRoot -TargetPath $tempDir -DestinationRoot $tempRoot
                Remove-Item -LiteralPath $tempDir -Recurse -Force
            }
        }
    }
}

# ─── Main ─────────────────────────────────────────────────────────────────────

try {
    Write-Host ""
    Write-Host "Agent Skills installer" -ForegroundColor Green
    Write-Host "Source root: $SourceRoot" -ForegroundColor DarkGray
    Write-Host ""

    # ── Skills flow ──
    $skills = Get-SkillDirectories -RootPath $SourceRoot
    $selectedSkills = @(Select-Skills -Skills $skills)
    if ($selectedSkills.Count -eq 0) {
        throw "No skills selected."
    }

    $resolvedFormat = Select-Format
    $resolvedLayout = Select-Layout
    Assert-UniqueArtifactNames -SelectedSkills $selectedSkills -LayoutChoice $resolvedLayout
    $destinationRoot = Select-Destination
    Write-Step ("Checking source and destination paths for {0} selected skill(s)" -f $selectedSkills.Count)
    Assert-SafeInstallTargets -SelectedSkills $selectedSkills -SourceSkills $skills -DestinationRoot $destinationRoot -LayoutChoice $resolvedLayout -FormatChoice $resolvedFormat

    Write-Host ""
    Write-Info "Selected $($selectedSkills.Count) skill(s)"
    Write-Info "Destination root: $destinationRoot"
    Write-Info "Format: $resolvedFormat"
    Write-Info "Layout: $resolvedLayout"
    Write-Host ""

    Validate-SelectedSkills -SelectedSkills $selectedSkills

    switch ($resolvedFormat) {
        'folder' { Install-AsFolders -SelectedSkills $selectedSkills -SourceSkills $skills -DestinationRoot $destinationRoot -LayoutChoice $resolvedLayout }
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
