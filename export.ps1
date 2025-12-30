function Export-RepoWithContent {
    param($OutputFile = "Daagent_current_$(Get-Date -Format 'yyyyMMdd_HHmm').md")

    # Build content in memory first
    $content = @()
    $content += "# Complete Daagent Repository Analysis"
    $content += "Generated: $(Get-Date)"
    $content += ""

    # Directory tree
    $content += "## Directory Structure"
    $content += ""
    $content += ((tree /F) -split "`n" | Where-Object { $_ -notlike "*venv*" } | Out-String)
    $content += ""

    # File contents
    $content += "## File Contents"
    $content += ""

    Get-ChildItem -Recurse -File | Where-Object {
        $_.Extension -match '\.(py|md|txt|json|yml|yaml|js|html|css|env|ps1|pyc|TAG)$' -and $_.FullName -notlike "*\venv\*"
    } | ForEach-Object {
        $content += ""
        $content += "### File: $($_.FullName)"
        $content += ""
        $content += "``````$($_.Extension.TrimStart('.'))"
        try {
            $content += Get-Content $_.FullName -Raw
        }
        catch {
            $content += "Error reading file: $_"
        }
        $content += "``````"
    }

    # Write all at once (prevents lock issues)
    $content | Out-File $OutputFile -Encoding UTF8
    Write-Host "Created: $OutputFile"
}

# Run it
Export-RepoWithContent