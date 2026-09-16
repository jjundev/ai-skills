[CmdletBinding()]
param(
    # Override this when the script is copied outside the repository.
    [string]$ProjectRoot = '',

    # Keep recoverable copies of replaced global skill directories here.
    [string]$BackupRoot = (Join-Path ([Environment]::GetFolderPath('UserProfile')) '.ai-skills-backup')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

function Test-SkillDirectory {
    param([System.IO.DirectoryInfo]$Directory)

    return Test-Path -LiteralPath (Join-Path $Directory.FullName 'SKILL.md')
}

function New-SkillJunction {
    param(
        [string]$LinkPath,
        [string]$TargetPath
    )

    New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null
}

function Save-ExistingDirectory {
    param(
        [System.IO.DirectoryInfo]$Directory,
        [string]$RootName
    )

    $backupDirectory = Join-Path $BackupRoot (Get-Date -Format 'yyyyMMdd-HHmmss')
    New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
    $destination = Join-Path $backupDirectory ("{0}--{1}" -f $RootName, $Directory.Name)
    Move-Item -LiteralPath $Directory.FullName -Destination $destination
    Write-Host ("  backup: {0} -> {1}" -f $Directory.FullName, $destination)
}

$globalRoots = @(
    [PSCustomObject]@{ Name = 'agents';              Path = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.agents\skills' },
    [PSCustomObject]@{ Name = 'antigravity-config';  Path = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.gemini\config\skills' },
    [PSCustomObject]@{ Name = 'antigravity-cli';     Path = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.gemini\antigravity-cli\skills' },
    [PSCustomObject]@{ Name = 'claude';              Path = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.claude\skills' },
    [PSCustomObject]@{ Name = 'codex';               Path = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\skills' },
    # Compatibility mirror for older Antigravity builds that used this path.
    [PSCustomObject]@{ Name = 'antigravity-legacy';  Path = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.gemini\antigravity\.agents\skills' }
)

if (-not (Test-Path -LiteralPath $ProjectRoot)) {
    throw "Project root does not exist: $ProjectRoot"
}

$skillDirectories = @{}
Get-ChildItem -LiteralPath $ProjectRoot -Force -Directory | Where-Object {
    Test-SkillDirectory $_
} | ForEach-Object {
    $skillDirectories[$_.Name] = $_.FullName
}

Write-Host "Central skill repository: $ProjectRoot"
Write-Host ("Existing managed skills: {0}" -f $skillDirectories.Count)

# First absorb valid skills that exist only in a global store. Existing project
# versions remain canonical; conflicting global directories are backed up.
foreach ($root in $globalRoots) {
    if (-not (Test-Path -LiteralPath $root.Path)) {
        continue
    }

    Write-Host "`nScanning $($root.Name): $($root.Path)"
    $entries = @(Get-ChildItem -LiteralPath $root.Path -Force -Directory)

    foreach ($entry in $entries) {
        # Codex owns these directories; they are runtime internals, not user
        # skills and should not be moved into the repository.
        if ($root.Name -eq 'codex' -and $entry.Name -in @('.system', 'codex-primary-runtime')) {
            Write-Host "  keep runtime directory: $($entry.Name)"
            continue
        }

        if (-not (Test-SkillDirectory $entry)) {
            Write-Host "  keep unmanaged directory: $($entry.Name)"
            continue
        }

        if ($skillDirectories.ContainsKey($entry.Name)) {
            if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                # A link can be safely replaced without touching its target.
                Remove-Item -LiteralPath $entry.FullName -Recurse -Force
                New-SkillJunction -LinkPath $entry.FullName -TargetPath $skillDirectories[$entry.Name]
                Write-Host "  relink: $($entry.Name)"
            }
            else {
                Save-ExistingDirectory -Directory $entry -RootName $root.Name
                New-SkillJunction -LinkPath $entry.FullName -TargetPath $skillDirectories[$entry.Name]
                Write-Host "  replace with junction: $($entry.Name)"
            }
            continue
        }

        $destination = Join-Path $ProjectRoot $entry.Name
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            # Preserve a linked skill's contents in the central repository,
            # then replace this link with a direct link to the repository.
            Copy-Item -LiteralPath $entry.FullName -Destination $destination -Recurse
            Write-Host "  import linked skill: $($entry.Name)"
        }
        else {
            Move-Item -LiteralPath $entry.FullName -Destination $destination
            Write-Host "  import skill: $($entry.Name)"
        }
        $skillDirectories[$entry.Name] = $destination
    }
}

# Expose every central skill in every supported global store. Unmanaged
# directories (for example Claude extensions or Codex internals) remain where
# their host application placed them.
foreach ($root in $globalRoots) {
    New-Item -ItemType Directory -Path $root.Path -Force | Out-Null
    Write-Host "`nLinking skills into $($root.Name)"

    foreach ($skillName in @($skillDirectories.Keys | Sort-Object)) {
        $linkPath = Join-Path $root.Path $skillName
        $targetPath = $skillDirectories[$skillName]

        if (Test-Path -LiteralPath $linkPath) {
            $existing = Get-Item -LiteralPath $linkPath -Force
            if ($existing.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                Remove-Item -LiteralPath $linkPath -Recurse -Force
            }
            elseif (-not (Test-SkillDirectory $existing)) {
                Write-Warning "Cannot link '$linkPath': a non-skill directory already exists."
                continue
            }
            else {
                Save-ExistingDirectory -Directory $existing -RootName $root.Name
            }
        }

        New-SkillJunction -LinkPath $linkPath -TargetPath $targetPath
    }
}

Write-Host "`nDone. Global skill stores now reference: $ProjectRoot"
Write-Host "Backups (only when replacements were needed): $BackupRoot"
