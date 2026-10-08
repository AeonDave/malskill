$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $repoRoot 'install.ps1'
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('malskill-ps1-test-' + [guid]::NewGuid())
$testRoot = [System.IO.Path]::GetFullPath($testRoot)
$python = (Get-Command python -ErrorAction Stop).Source
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$checks = 0

function Assert-Test([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
    $script:checks++
}

function Assert-Throws([scriptblock]$Action, [string]$Expected) {
    $message = ''
    try { & $Action } catch { $message = $_.Exception.Message }
    Assert-Test ($message -like "*$Expected*") "Expected '$Expected'; got '$message'"
}

function New-FixtureSkill([string]$PathValue) {
    [System.IO.Directory]::CreateDirectory($PathValue) | Out-Null
    $name = Split-Path -Path $PathValue -Leaf
    [System.IO.File]::WriteAllText((Join-Path $PathValue 'SKILL.md'), "---`nname: $name`ndescription: Test installer fixture.`n---`n`n# Fixture`n")
    [System.IO.File]::WriteAllText((Join-Path $PathValue 'payload.txt'), "payload-$name")
}

function Invoke-FixtureInstall([string]$Root, [string]$Target, [string]$OutputFormat, [string]$OutputLayout, [string[]]$References = @(), [bool]$ExpectSuccess = $true) {
    $arguments = @('-NoProfile', '-File', $installer, '-SourceRoot', $Root, '-Destination', $Target, '-Format', $OutputFormat, '-Layout', $OutputLayout)
    if ($References.Count -eq 0) { $arguments += '-All' }
    else { $arguments += @('-SkillRefs') + $References }
    $output = @(& $pwsh @arguments 2>&1)
    $exitCode = $LASTEXITCODE
    Assert-Test (($exitCode -eq 0) -eq $ExpectSuccess) "Unexpected installer exit $exitCode`: $($output -join "`n")"
    return $output -join "`n"
}

function Assert-Archive([string]$PathValue, [string]$SkillName) {
    Assert-Test (Test-Path -LiteralPath $PathValue -PathType Leaf) "Missing archive: $PathValue"
    $archive = [System.IO.Compression.ZipFile]::OpenRead($PathValue)
    try {
        $names = @($archive.Entries | ForEach-Object FullName)
        Assert-Test ($names -contains "$SkillName/SKILL.md") "Missing skill root in $PathValue"
        Assert-Test ($names -contains "$SkillName/payload.txt") "Missing payload in $PathValue"
    } finally { $archive.Dispose() }
}

New-Item -ItemType Directory -Path $testRoot | Out-Null
$oldSelectorLog = $env:MALSKILL_SELECTOR_TEST_LOG
$oldSelectorPaths = $env:MALSKILL_SELECTOR_TEST_PATHS
$oldSelectorExit = $env:MALSKILL_SELECTOR_TEST_EXIT
try {
    $tokens = $null
    $parseErrors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseFile($installer, [ref]$tokens, [ref]$parseErrors)
    Assert-Test ($parseErrors.Count -eq 0) "Installer parser errors: $parseErrors"
    foreach ($definition in $ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
        . ([scriptblock]::Create($definition.Extent.Text))
    }

    $ScriptDir = $repoRoot
    $SourceRoot = Join-Path $testRoot 'fixture-root'
    $DiscoveryExclusions = @('dist', 'installed-skills', 'node_modules', '__pycache__')
    New-FixtureSkill $SourceRoot
    New-FixtureSkill (Join-Path $SourceRoot 'techniques/child')
    New-FixtureSkill (Join-Path $SourceRoot 'level/one/two/deep')
    New-FixtureSkill (Join-Path $SourceRoot '.hidden/ignored')
    New-FixtureSkill (Join-Path $SourceRoot 'installed-skills/ignored')
    $discovered = @(Get-SkillDirectories $SourceRoot)
    Assert-Test ($discovered.Count -eq 3) 'Discovery must retain root and arbitrary nesting, and exclude hidden/install folders.'
    Assert-Test (($discovered.RelativePath -join ',') -eq '.,level/one/two/deep,techniques/child') 'Incorrect normalized discovery paths.'
    $selected = @(Resolve-SkillReferences -Skills $discovered -References @('techniques\child', '.'))
    Assert-Test (($selected.RelativePath -join ',') -eq '.,techniques/child') 'References must preserve root and separator normalization.'
    Assert-Throws { Resolve-SkillReferences -Skills $discovered -References @('missing') } 'Skill reference not found'

    $SelectorScript = Join-Path $testRoot 'selector_stub.py'
    [System.IO.File]::WriteAllText($SelectorScript, @'
import json
import os
from pathlib import Path
import sys
skills_file = Path(sys.argv[sys.argv.index('--skills-file') + 1])
records = json.loads(skills_file.read_text(encoding='utf-8'))
assert isinstance(records, list)
assert all(set(record) == {'name', 'path'} for record in records)
Path(os.environ['MALSKILL_SELECTOR_TEST_LOG']).write_text(str(skills_file), encoding='utf-8')
paths = os.environ.get('MALSKILL_SELECTOR_TEST_PATHS', '')
if paths:
    print(paths)
raise SystemExit(int(os.environ.get('MALSKILL_SELECTOR_TEST_EXIT', '0')))
'@)
    $PythonInvocation = @{ Exe = $python; PrefixArgs = @() }
    $env:MALSKILL_SELECTOR_TEST_LOG = Join-Path $testRoot 'selector-log.txt'
    $env:MALSKILL_SELECTOR_TEST_PATHS = ".`ntechniques/child`ntechniques/child"
    $env:MALSKILL_SELECTOR_TEST_EXIT = '0'
    $All = $false
    $SkillRefs = @()
    $selected = @(Select-Skills $discovered)
    Assert-Test (($selected.RelativePath -join ',') -eq '.,techniques/child') 'Selector paths must map to source objects without duplicates.'
    $selectorTempFile = [System.IO.File]::ReadAllText($env:MALSKILL_SELECTOR_TEST_LOG)
    Assert-Test (-not (Test-Path -LiteralPath $selectorTempFile)) 'Selector input must be cleaned after success.'
    $env:MALSKILL_SELECTOR_TEST_PATHS = 'Techniques/child'
    Assert-Throws { Select-Skills $discovered } 'unknown skill path'
    $selectorTempFile = [System.IO.File]::ReadAllText($env:MALSKILL_SELECTOR_TEST_LOG)
    Assert-Test (-not (Test-Path -LiteralPath $selectorTempFile)) 'Selector input must be cleaned after malformed output.'
    $env:MALSKILL_SELECTOR_TEST_EXIT = '130'
    Assert-Throws { Select-Skills $discovered } 'selection cancelled or failed'
    $selectorTempFile = [System.IO.File]::ReadAllText($env:MALSKILL_SELECTOR_TEST_LOG)
    Assert-Test (-not (Test-Path -LiteralPath $selectorTempFile)) 'Selector input must be cleaned after cancellation.'
    $env:MALSKILL_SELECTOR_TEST_EXIT = '0'
    $env:MALSKILL_SELECTOR_TEST_PATHS = 'grüp/élève'
    $unicodeSkill = [pscustomobject]@{ Name = 'élève'; RelativePath = 'grüp/élève'; FullPath = 'unused' }
    $selected = @(Select-Skills @($unicodeSkill))
    Assert-Test ($selected.Count -eq 1 -and $selected[0].RelativePath -ceq 'grüp/élève') 'Single-skill JSON arrays and UTF-8 selector paths must survive capture.'
    $SelectorScript = Join-Path $testRoot 'missing-selector.py'
    $All = $true
    Assert-Test (@(Select-Skills $discovered).Count -eq 3) '-All must bypass the selector.'
    $All = $false
    $SkillRefs = @('child')
    Assert-Test (@(Select-Skills $discovered)[0].Name -eq 'child') '-SkillRefs must bypass the selector.'

    foreach ($outputFormat in @('folder', 'skill', 'zip')) {
        foreach ($outputLayout in @('flat', 'group')) {
            $target = Join-Path $testRoot "$outputFormat-$outputLayout"
            Invoke-FixtureInstall $SourceRoot $target $outputFormat $outputLayout | Out-Null
            $childRelative = if ($outputLayout -eq 'group') { 'techniques/child' } else { 'child' }
            $deepRelative = if ($outputLayout -eq 'group') { 'level/one/two/deep' } else { 'deep' }
            if ($outputFormat -eq 'folder') {
                Assert-Test (Test-Path -LiteralPath (Join-Path $target 'fixture-root/SKILL.md')) 'Missing standalone root folder.'
                Assert-Test (Test-Path -LiteralPath (Join-Path $target "$childRelative/SKILL.md")) 'Missing child folder.'
                Assert-Test (Test-Path -LiteralPath (Join-Path $target "$deepRelative/SKILL.md")) 'Missing deeply nested folder.'
            } else {
                Assert-Archive (Join-Path $target "fixture-root.$outputFormat") 'fixture-root'
                Assert-Archive (Join-Path $target "$childRelative.$outputFormat") 'child'
                Assert-Archive (Join-Path $target "$deepRelative.$outputFormat") 'deep'
            }
        }
    }
    $overwriteTarget = Join-Path $testRoot 'folder-flat'
    [System.IO.File]::WriteAllText((Join-Path $overwriteTarget 'child/stale.txt'), 'old')
    Invoke-FixtureInstall $SourceRoot $overwriteTarget 'folder' 'flat' @('child') | Out-Null
    Assert-Test (-not (Test-Path -LiteralPath (Join-Path $overwriteTarget 'child/stale.txt'))) 'Folder overwrite must remove stale files.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $SourceRoot 'techniques/child/payload.txt')) 'Folder overwrite altered its source.'
    Invoke-FixtureInstall $SourceRoot (Join-Path $testRoot 'skill-flat') 'skill' 'flat' @('child') | Out-Null
    Assert-Archive (Join-Path $testRoot 'skill-flat/child.skill') 'child'

    $existingArchive = Join-Path $testRoot 'skill-flat/child.skill'
    $archiveBefore = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($existingArchive))
    $PackagerScript = Join-Path $testRoot 'failing_packager.py'
    [System.IO.File]::WriteAllText($PackagerScript, @'
import os
from pathlib import Path
import sys
Path(os.environ['MALSKILL_SELECTOR_TEST_LOG']).write_text(sys.argv[2], encoding='utf-8')
Path(sys.argv[2], 'child.skill').write_text('partial archive', encoding='utf-8')
raise SystemExit(2)
'@)
    $child = @($discovered | Where-Object Name -eq 'child')
    Assert-Throws { Install-AsArchives $child (Join-Path $testRoot 'skill-flat') 'flat' 'skill' } 'Python script failed'
    Assert-Test ([Convert]::ToBase64String([System.IO.File]::ReadAllBytes($existingArchive)) -ceq $archiveBefore) 'Packaging failure must preserve the existing archive.'
    $packagerTempDir = [System.IO.File]::ReadAllText($env:MALSKILL_SELECTOR_TEST_LOG)
    Assert-Test (-not (Test-Path -LiteralPath $packagerTempDir)) 'Failed package staging must be cleaned.'

    $duplicateRoot = Join-Path $testRoot 'duplicates'
    New-FixtureSkill (Join-Path $duplicateRoot 'first/same')
    New-FixtureSkill (Join-Path $duplicateRoot 'second/same')
    $duplicateTarget = Join-Path $testRoot 'duplicate-flat'
    $failure = Invoke-FixtureInstall $duplicateRoot $duplicateTarget 'folder' 'flat' @() $false
    Assert-Test ($failure -like '*would collide*') 'Flat duplicate collision should explain the failure.'
    Assert-Test (-not (Test-Path -LiteralPath $duplicateTarget)) 'Collision must fail before writing.'
    Invoke-FixtureInstall $duplicateRoot (Join-Path $testRoot 'duplicate-group') 'folder' 'group' | Out-Null
    Assert-Test (Test-Path -LiteralPath (Join-Path $testRoot 'duplicate-group/first/same/SKILL.md')) 'Grouped duplicate install lost first skill.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $testRoot 'duplicate-group/second/same/SKILL.md')) 'Grouped duplicate install lost second skill.'
    $rootCollisionSource = Join-Path $testRoot 'bundle'
    New-FixtureSkill $rootCollisionSource
    New-FixtureSkill (Join-Path $rootCollisionSource 'bundle')
    $rootPayloadBefore = [System.IO.File]::ReadAllText((Join-Path $rootCollisionSource 'payload.txt'))
    $childPayloadBefore = [System.IO.File]::ReadAllText((Join-Path $rootCollisionSource 'bundle/payload.txt'))
    foreach ($outputFormat in @('folder', 'skill', 'zip')) {
        $target = Join-Path $testRoot "root-collision-$outputFormat"
        $failure = Invoke-FixtureInstall $rootCollisionSource $target $outputFormat 'group' @() $false
        Assert-Test ($failure -like '*would collide*') "Root/name collision should fail for $outputFormat."
        Assert-Test (-not (Test-Path -LiteralPath $target)) "Root/name collision must fail before writing $outputFormat output."
        Assert-Test ([System.IO.File]::ReadAllText((Join-Path $rootCollisionSource 'payload.txt')) -ceq $rootPayloadBefore) 'Root collision altered the source root.'
        Assert-Test ([System.IO.File]::ReadAllText((Join-Path $rootCollisionSource 'bundle/payload.txt')) -ceq $childPayloadBefore) 'Root collision altered the nested source.'
    }
    $failure = Invoke-FixtureInstall $duplicateRoot (Join-Path $testRoot 'ambiguous') 'zip' 'group' @('same') $false
    Assert-Test ($failure -like '*Ambiguous skill reference*') 'Ambiguous bare names must fail.'
    $failure = Invoke-FixtureInstall $SourceRoot (Join-Path $testRoot 'invalid') 'folder' 'flat' @('missing') $false
    Assert-Test ($failure -like '*Skill reference not found*') 'Invalid references must fail.'

    $failure = Invoke-FixtureInstall $SourceRoot $SourceRoot 'folder' 'group' @() $false
    Assert-Test ($failure -like '*overlaps*') 'Installing onto source must fail before deleting it.'
    $nestedTarget = Join-Path $SourceRoot 'nested-output'
    $failure = Invoke-FixtureInstall $SourceRoot $nestedTarget 'zip' 'group' @('child') $false
    Assert-Test ($failure -like '*overlaps*') 'Packaging inside a source skill must fail.'
    Assert-Test (-not (Test-Path -LiteralPath $nestedTarget)) 'Nested overlap must fail before writing.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $SourceRoot 'SKILL.md')) 'Self-overlap deleted the source root.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $SourceRoot 'techniques/child/payload.txt')) 'Source-overlap damaged a nested skill.'

    $unselectedRoot = Join-Path $testRoot 'unselected'
    New-FixtureSkill (Join-Path $unselectedRoot 'leaf')
    New-FixtureSkill (Join-Path $unselectedRoot 'other/leaf')
    $failure = Invoke-FixtureInstall $unselectedRoot $unselectedRoot 'folder' 'flat' @('other/leaf') $false
    Assert-Test ($failure -like '*overlaps*') 'An unselected source must also be protected from deletion.'
    Assert-Test (Test-Path -LiteralPath (Join-Path $unselectedRoot 'leaf/payload.txt')) 'Unselected source was damaged.'

    $originalSourceRoot = $SourceRoot
    try {
        $SourceRoot = $unselectedRoot
        $protectedSources = @(Get-SkillDirectories $SourceRoot)
        Assert-InstallSourceSeparation (Join-Path $SourceRoot 'leaf-suffix/output') $protectedSources
        Assert-Test $true 'A sibling sharing a source name prefix must remain allowed.'
        Assert-Throws { Assert-InstallSourceSeparation (Join-Path $SourceRoot 'leaf/inside') $protectedSources } 'overlaps'
        Assert-Throws { Assert-InstallSourceSeparation (Join-Path $SourceRoot 'other/../leaf') $protectedSources } 'overlaps'
        Assert-Throws { Assert-InstallSourceSeparation (Split-Path $SourceRoot -Parent) $protectedSources } 'overlaps'
        if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) {
            Assert-Throws { Assert-InstallSourceSeparation ((Join-Path $SourceRoot 'LEAF/inside').ToUpperInvariant()) $protectedSources } 'overlaps'
        }
    } finally { $SourceRoot = $originalSourceRoot }

    $boundaryRoot = Join-Path $testRoot 'destination'
    Assert-Throws { Assert-InstallTargetWithinRoot $boundaryRoot $boundaryRoot } 'inside the destination root'
    Assert-Throws { Assert-InstallTargetWithinRoot (Join-Path $testRoot 'destination-suffix/skill') $boundaryRoot } 'inside the destination root'
    if ([System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT) {
        $junction = Join-Path $testRoot 'linked-destination'
        New-Item -ItemType Junction -Path $junction -Target $SourceRoot | Out-Null
        $failure = Invoke-FixtureInstall $SourceRoot $junction 'folder' 'flat' @('child') $false
        Assert-Test ($failure -like '*symbolic link or junction*') 'Junction destinations must not bypass source protection.'
        Assert-Test (Test-Path -LiteralPath (Join-Path $SourceRoot 'SKILL.md')) 'Junction overlap damaged its source.'
        Remove-Item -LiteralPath $junction -Force

        $postCheckTarget = Join-Path $testRoot 'post-check-target'
        Assert-SafeInstallTargets $child $discovered $postCheckTarget 'flat' 'folder'
        New-Item -ItemType Junction -Path $postCheckTarget -Target $SourceRoot | Out-Null
        Assert-Throws { Install-AsFolders $child $discovered $postCheckTarget 'flat' } 'symbolic link or junction'
        Assert-Test (Test-Path -LiteralPath (Join-Path $SourceRoot 'techniques/child/payload.txt')) 'A junction introduced after preflight damaged its source.'
        Remove-Item -LiteralPath $postCheckTarget -Force
    }
    Write-Host "PASS: $checks PowerShell installer assertions"
}
finally {
    $env:MALSKILL_SELECTOR_TEST_LOG = $oldSelectorLog
    $env:MALSKILL_SELECTOR_TEST_PATHS = $oldSelectorPaths
    $env:MALSKILL_SELECTOR_TEST_EXIT = $oldSelectorExit
    if (Test-Path -LiteralPath $testRoot) {
        $resolvedTestRoot = (Resolve-Path -LiteralPath $testRoot).Path
        $tempPrefix = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
        if ($resolvedTestRoot -ne $testRoot -or -not $resolvedTestRoot.StartsWith($tempPrefix, [System.StringComparison]::OrdinalIgnoreCase) -or
            (Split-Path -Path $resolvedTestRoot -Leaf) -notlike 'malskill-ps1-test-*') {
            throw "Unsafe test cleanup path: $resolvedTestRoot"
        }
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
