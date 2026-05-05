param(
    [string]$SourceRoot = "",
    [string]$Destination = "",
    [ValidateSet("folder", "skill", "zip", "")]
    [string]$Format = "",
    [ValidateSet("flat", "group", "")]
    [string]$Layout = "",
    [string[]]$SkillRefs = @(),
    [switch]$All,
    [ValidateSet("skills", "commands", "")]
    [string]$Action = "",
    [ValidateSet("claude-code", "codex", "cursor", "windsurf", "copilot", "gemini", "")]
    [string]$Agent = "",
    [ValidateSet("global", "project", "")]
    [string]$Scope = ""
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

# ─── Skills discovery ────────────────────────────────────────────────────────

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
    $indexWidth = $Skills.Count.ToString().Length
    for ($i = 0; $i -lt $Skills.Count; $i++) {
        $index = $i + 1
        Write-Host ("[{0,$indexWidth}] {1}" -f $index, $Skills[$i].RelativePath) -ForegroundColor Cyan
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

# ─── Commands flow ────────────────────────────────────────────────────────────

$AgentSourceFile = @{
    'claude-code' = 'claude-code.md'
    'codex'       = 'codex.md'
    'cursor'      = 'cursor.md'
    'windsurf'    = 'windsurf.md'
    'copilot'     = 'copilot.md'
    'gemini'      = 'gemini.md'
}

$AgentProjectOnly = @('windsurf', 'copilot')

function Get-SkillDescription([string]$SkillDir) {
    $skillFile = Join-Path $SkillDir "SKILL.md"
    try {
        $content = Get-Content -LiteralPath $skillFile -Raw -ErrorAction Stop
        if ($content -match '(?s)^---\r?\n(.*?)\r?\n---') {
            $frontmatter = $Matches[1]
            # Block scalar (description: |)
            if ($frontmatter -match '(?s)description:\s*\|\r?\n[ \t]+([^\r\n]+)') {
                return $Matches[1].Trim()
            }
            # Single line
            if ($frontmatter -match 'description:\s*(.+)') {
                return $Matches[1].Trim(' ', '"', "'")
            }
        }
    } catch {}
    return ""
}

function Get-CommandDefinitions([string]$RootPath) {
    $commandDirs = Get-ChildItem -Path $RootPath -Recurse -Directory -Force |
        Where-Object { $_.Name -eq '.commands' }

    $commands = foreach ($dir in $commandDirs) {
        $parentDir = $dir.Parent.FullName
        $skillFile = Join-Path $parentDir "SKILL.md"
        if (-not (Test-Path -LiteralPath $skillFile)) { continue }

        $name = $dir.Parent.Name
        $description = Get-SkillDescription -SkillDir $parentDir
        $relPath = Get-RelativePathNormalized -BasePath $RootPath -TargetPath $parentDir

        $availableAgents = @(
            Get-ChildItem -Path $dir.FullName -File -Filter "*.md" -Force |
            ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_.Name) } |
            Where-Object { $AgentSourceFile.ContainsKey($_) }
        )

        if ($availableAgents.Count -eq 0) { continue }

        [pscustomobject]@{
            Name            = $name
            Description     = $description
            RelativePath    = $relPath
            CommandDir      = $dir.FullName
            AvailableAgents = $availableAgents
        }
    }

    return @($commands | Sort-Object RelativePath, Name)
}

function Get-AgentCommandPath([string]$AgentName, [string]$CommandName, [string]$ScopeChoice) {
    $homeDir = [Environment]::GetFolderPath('UserProfile')
    $cwd = (Get-Location).Path

    switch ($AgentName) {
        'claude-code' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.claude', 'commands', "$CommandName.md")
        }
        'codex' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.codex', 'skills', "$CommandName.md")
        }
        'cursor' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.cursor', 'rules', "$CommandName.mdc")
        }
        'windsurf' {
            return [System.IO.Path]::Combine($cwd, '.windsurf', 'rules', "$CommandName.md")
        }
        'copilot' {
            return [System.IO.Path]::Combine($cwd, '.github', 'instructions', "$CommandName.instructions.md")
        }
        'gemini' {
            if ($ScopeChoice -eq 'global') {
                return [System.IO.Path]::Combine($homeDir, '.gemini', 'skills', "$CommandName.md")
            }
            return [System.IO.Path]::Combine($cwd, '.gemini', "$CommandName.md")
        }
        default { throw "Unknown agent: $AgentName" }
    }
}

function Get-AgentSkillPath([string]$AgentName, [string]$CommandName, [string]$ScopeChoice) {
    $homeDir = [Environment]::GetFolderPath('UserProfile')
    $cwd = (Get-Location).Path

    switch ($AgentName) {
        'claude-code' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.claude', 'skills', $CommandName)
        }
        'codex' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.codex', 'skills', $CommandName)
        }
        'cursor' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.cursor', 'skills', $CommandName)
        }
        'windsurf' {
            return [System.IO.Path]::Combine($cwd, '.windsurf', 'skills', $CommandName)
        }
        'copilot' {
            return [System.IO.Path]::Combine($cwd, '.github', 'skills', $CommandName)
        }
        'gemini' {
            $base = if ($ScopeChoice -eq 'global') { $homeDir } else { $cwd }
            return [System.IO.Path]::Combine($base, '.gemini', 'skills', $CommandName)
        }
        default { throw "Unknown agent: $AgentName" }
    }
}

function Choose-Agent([string[]]$AvailableAgents) {
    if (-not [string]::IsNullOrWhiteSpace($Agent)) {
        if ($AvailableAgents -notcontains $Agent) {
            throw "Agent '$Agent' has no command file in selected commands."
        }
        return $Agent
    }

    $ordered = @('claude-code', 'codex', 'cursor', 'windsurf', 'copilot', 'gemini') |
        Where-Object { $AvailableAgents -contains $_ }

    Write-Step "Select target agent"
    for ($i = 0; $i -lt $ordered.Count; $i++) {
        Write-Host ("[{0}] {1}" -f ($i + 1), $ordered[$i]) -ForegroundColor Cyan
    }
    $choice = Read-Host "Select agent"
    $idx = 0
    if (-not [int]::TryParse($choice.Trim(), [ref]$idx) -or $idx -lt 1 -or $idx -gt $ordered.Count) {
        throw "Invalid agent selection: $choice"
    }
    return $ordered[$idx - 1]
}

function Choose-CommandScope([string]$AgentName, [string]$CommandName) {
    if (-not [string]::IsNullOrWhiteSpace($Scope)) {
        return $Scope
    }
    if ($AgentProjectOnly -contains $AgentName) {
        return 'project'
    }

    $globalPath = Get-AgentCommandPath -AgentName $AgentName -CommandName $CommandName -ScopeChoice 'global'
    $projectPath = Get-AgentCommandPath -AgentName $AgentName -CommandName $CommandName -ScopeChoice 'project'

    Write-Step "Select install scope"
    Write-Host ("[1] global  — {0}" -f $globalPath) -ForegroundColor Cyan
    Write-Host ("[2] project — {0}" -f $projectPath) -ForegroundColor Cyan
    $choice = Read-Host "Select scope"
    switch ($choice.Trim()) {
        '1' { return 'global' }
        '2' { return 'project' }
        default { throw "Invalid scope selection: $choice" }
    }
}

function Install-CommandFiles([object[]]$SelectedCommands, [string]$AgentName, [string]$ScopeChoice) {
    $sourceFile = $AgentSourceFile[$AgentName]

    foreach ($cmd in $SelectedCommands) {
        $src = Join-Path $cmd.CommandDir $sourceFile
        if (-not (Test-Path -LiteralPath $src)) {
            Write-Warn "No $AgentName command file found for '$($cmd.Name)' — skipping"
            continue
        }

        $dest = Get-AgentCommandPath -AgentName $AgentName -CommandName $cmd.Name -ScopeChoice $ScopeChoice
        $destDir = Split-Path -Parent $dest
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null

        if (Test-Path -LiteralPath $dest) {
            Write-Warn "Overwriting existing: $dest"
        }

        Write-Step "Installing $($cmd.Name) → $dest"
        Copy-Item -LiteralPath $src -Destination $dest -Force
        Write-Info "$($cmd.Name) command installed for $AgentName"

        $skillSrc = Split-Path -Parent $cmd.CommandDir
        $skillDest = Get-AgentSkillPath -AgentName $AgentName -CommandName $cmd.Name -ScopeChoice $ScopeChoice
        $skillDestParent = Split-Path -Parent $skillDest
        New-Item -ItemType Directory -Path $skillDestParent -Force | Out-Null

        if (Test-Path -LiteralPath $skillDest) {
            Write-Warn "Removing existing skill: $skillDest"
            Remove-Item -LiteralPath $skillDest -Recurse -Force
        }

        Write-Step "Installing skill $($cmd.Name) → $skillDest"
        Copy-Item -LiteralPath $skillSrc -Destination $skillDest -Recurse -Force
        Write-Info "$($cmd.Name) skill installed"
    }
}

function Invoke-CommandsFlow {
    $commands = Get-CommandDefinitions -RootPath $SourceRoot
    if ($commands.Count -eq 0) {
        throw "No .commands/ folders found under $SourceRoot"
    }

    Write-Step "Found $($commands.Count) command(s)"
    $indexWidth = $commands.Count.ToString().Length
    for ($i = 0; $i -lt $commands.Count; $i++) {
        $agents = $commands[$i].AvailableAgents -join ', '
        $rawDesc = $commands[$i].Description
        if ($rawDesc) {
            $dotIdx = $rawDesc.IndexOf('.')
            if ($dotIdx -ge 0) { $rawDesc = $rawDesc.Substring(0, $dotIdx + 1) }
            $desc = " — $rawDesc"
        } else { $desc = "" }
        Write-Host ("[{0,$indexWidth}] {1}{2}  [{3}]" -f ($i + 1), $commands[$i].Name, $desc, $agents) -ForegroundColor Cyan
    }
    Write-Host ""
    $rawSelection = Read-Host "Select commands by index (e.g. 1,3-5 or all)"
    $indexes = Parse-IndexSelection -RawSelection $rawSelection -MaxIndex $commands.Count
    $selectedCommands = @(foreach ($index in $indexes) { $commands[$index - 1] })

    if ($selectedCommands.Count -eq 0) {
        throw "No commands selected."
    }

    $allAvailable = @($selectedCommands | ForEach-Object { $_.AvailableAgents } | Sort-Object -Unique)
    $chosenAgent = Choose-Agent -AvailableAgents $allAvailable
    $chosenScope = Choose-CommandScope -AgentName $chosenAgent -CommandName $selectedCommands[0].Name

    Write-Host ""
    Write-Info "Selected $($selectedCommands.Count) command(s)"
    Write-Info "Agent: $chosenAgent"
    Write-Info "Scope: $chosenScope"
    Write-Host ""

    Install-CommandFiles -SelectedCommands $selectedCommands -AgentName $chosenAgent -ScopeChoice $chosenScope

    Write-Host ""
    Write-Info "Command install complete."
}

# ─── Action selection ─────────────────────────────────────────────────────────

function Choose-Action {
    if (-not [string]::IsNullOrWhiteSpace($Action)) {
        return $Action
    }

    Write-Step "Select action"
    Write-Host "[1] Install skills   — copy skill directories or packages to a destination" -ForegroundColor Cyan
    Write-Host "[2] Install commands — register slash commands for AI agents (claude-code, cursor, etc.)" -ForegroundColor Cyan
    $choice = Read-Host "Select action"
    switch ($choice.Trim()) {
        '1' { return 'skills' }
        '2' { return 'commands' }
        default { throw "Invalid action: $choice" }
    }
}

# ─── Main ─────────────────────────────────────────────────────────────────────

try {
    Write-Host ""
    Write-Host "Agent Skills installer" -ForegroundColor Green
    Write-Host "Source root: $SourceRoot" -ForegroundColor DarkGray
    Write-Host ""

    $resolvedAction = Choose-Action
    Write-Host ""

    if ($resolvedAction -eq 'commands') {
        Invoke-CommandsFlow
        exit 0
    }

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
