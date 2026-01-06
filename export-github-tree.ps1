param(
    [string]$Path = ".github",
    [string]$OutputFile = "github-folder-tree.txt"
)

function Get-Tree {
    param(
        [string]$Path,
        [string]$Prefix = ""
    )

    $items = Get-ChildItem -Path $Path -ErrorAction SilentlyContinue | Sort-Object -Property @{Expression = {$_.PSIsContainer}; Descending = $true}, Name

    for ($i = 0; $i -lt $items.Count; $i++) {
        $item = $items[$i]
        $isLast = ($i -eq $items.Count - 1)
        $connector = if ($isLast) { "`-- " } else { "|-- " }
        $nextPrefix = if ($isLast) { "    " } else { "|   " }

        Write-Output "$Prefix$connector$($item.Name)"

        if ($item.PSIsContainer) {
            Get-Tree -Path $item.FullName -Prefix "$Prefix$nextPrefix"
        }
    }
}

function Export-FileContents {
    param(
        [string]$Path,
        [string]$OutputFile
    )

    $files = Get-ChildItem -Path $Path -File -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName

    foreach ($file in $files) {
        Write-Output "" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
        Write-Output "==================================================================================" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
        Write-Output "FILE: $($file.FullName)" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
        Write-Output "==================================================================================" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
        Write-Output "" | Out-File -FilePath $OutputFile -Append -Encoding UTF8

        try {
            $content = Get-Content -Path $file.FullName -Raw -ErrorAction Stop
            Write-Output $content | Out-File -FilePath $OutputFile -Append -Encoding UTF8
        } catch {
            Write-Output "[Error reading file: $($_.Exception.Message)]" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
        }
    }
}

Write-Output "GitHub Folder Tree Export with Contents" | Out-File -FilePath $OutputFile -Encoding UTF8
Write-Output "Generated on: $(Get-Date)" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output "Path: $Path" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output ("=" * 50) | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output "" | Out-File -FilePath $OutputFile -Append -Encoding UTF8

Write-Output "FOLDER STRUCTURE:" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output "" | Out-File -FilePath $OutputFile -Append -Encoding UTF8

Get-Tree -Path $Path | Out-File -FilePath $OutputFile -Append -Encoding UTF8

Write-Output "" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output ("=" * 80) | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output "FILE CONTENTS:" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output ("=" * 80) | Out-File -FilePath $OutputFile -Append -Encoding UTF8

Export-FileContents -Path $Path -OutputFile $OutputFile

Write-Output "" | Out-File -FilePath $OutputFile -Append -Encoding UTF8
Write-Output "Export complete. File saved as: $OutputFile" | Out-File -FilePath $OutputFile -Append -Encoding UTF8