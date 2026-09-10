$ErrorActionPreference = "Stop"

$configPath = Join-Path $PSScriptRoot "local_workbook_sync.config.ps1"
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Missing local configuration file: $configPath. Copy local_workbook_sync.config.ps1.example to local_workbook_sync.config.ps1 and set its values."
}

. $configPath

foreach ($setting in "WorkbookPath", "TeamTrackerBaseUrl", "WebhookToken") {
    if (-not (Get-Variable -Name $setting -ValueOnly -ErrorAction SilentlyContinue)) {
        throw "Missing required setting: `$$setting"
    }
}

if ($WebhookToken -eq "PASTE_RENDER_WEBHOOK_TOKEN_HERE") {
    throw "Set WebhookToken in $configPath to the Render WEBHOOK_TOKEN value."
}

if (-not (Test-Path -LiteralPath $WorkbookPath -PathType Leaf)) {
    throw "Workbook was not found: $WorkbookPath"
}

$content = [System.IO.File]::ReadAllBytes($WorkbookPath)
if ($content.Length -lt 4 -or $content[0] -ne 0x50 -or $content[1] -ne 0x4B -or $content[2] -ne 0x03 -or $content[3] -ne 0x04) {
    throw "Workbook is not a valid .xlsx or .xlsm file: $WorkbookPath"
}

$mode = if ($ImportMode) { $ImportMode } else { "replace" }
$token = [uri]::EscapeDataString($WebhookToken)
$baseUrl = $TeamTrackerBaseUrl.TrimEnd("/")
$syncUrl = "$baseUrl/api/imports/webhook?token=$token&mode=$mode"

try {
    $headers = @{ "X-Team-Tracker-Source" = "windows_task_scheduler_sync.xlsm" }
    $result = Invoke-RestMethod -Uri $syncUrl -Method Post -ContentType "application/vnd.ms-excel" -Headers $headers -Body $content -TimeoutSec 300
    $result | ConvertTo-Json -Depth 5
    if ($result.rejected_rows -gt 0) {
        exit 2
    }
} catch {
    $message = $_.Exception.Message
    if ($_.ErrorDetails.Message) {
        $message = "$message`n$($_.ErrorDetails.Message)"
    }
    Write-Error "Workbook sync failed: $message"
    exit 1
}
