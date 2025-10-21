param(
  [Parameter(Mandatory=$true)]
  [string]$Repo,            # e.g. yourname/yourrepo
  [string]$CsvPath = "issues_easy_path.csv"
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Write-Error "GitHub CLI 'gh' not found. Install from https://cli.github.com/ and authenticate with 'gh auth login'."
  exit 1
}

if (-not (Test-Path $CsvPath)) {
  Write-Error "CSV not found at $CsvPath"
  exit 1
}

$rows = Import-Csv -Path $CsvPath
$titleToNumber = @{}
$labelCache = @{}
$milestoneCache = @{}

function Ensure-Label {
  param([string]$Label)
  if (-not $Label) { return $false }
  if ($labelCache.ContainsKey($Label)) {
    return $labelCache[$Label]
  }
  gh label view $Label --repo $Repo *> $null
  if ($LASTEXITCODE -eq 0) {
    $labelCache[$Label] = $true
    return $true
  }
  gh label create $Label --repo $Repo --color ededed --description "" *> $null
  if ($LASTEXITCODE -eq 0) {
    $labelCache[$Label] = $true
    Write-Host "Created missing label '$Label'"
    return $true
  }
  $labelCache[$Label] = $false
  Write-Warning "Could not ensure label '$Label' exists. Skipping this label."
  return $false
}

function Ensure-Milestone {
  param([string]$Milestone)
  if (-not $Milestone) { return $false }
  if ($milestoneCache.ContainsKey($Milestone)) {
    return $milestoneCache[$Milestone]
  }
  gh milestone view $Milestone --repo $Repo *> $null
  if ($LASTEXITCODE -eq 0) {
    $milestoneCache[$Milestone] = $true
    return $true
  }
  gh milestone create $Milestone --repo $Repo *> $null
  if ($LASTEXITCODE -eq 0) {
    $milestoneCache[$Milestone] = $true
    Write-Host "Created missing milestone '$Milestone'"
    return $true
  }
  $milestoneCache[$Milestone] = $false
  Write-Warning "Could not ensure milestone '$Milestone' exists. Skipping this milestone."
  return $false
}

foreach ($row in $rows) {
  $labels = @()
  if ($row."Labels") {
    $labels = $row."Labels".Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
  }
  $labelArgs = @()
  foreach ($l in $labels) {
    if (Ensure-Label -Label $l) {
      $labelArgs += @("--label", $l)
    }
  }

  $milestoneArgs = @()
  if ($row."Milestone" -and $row."Milestone".Trim() -ne "") {
    $milestone = $row."Milestone".Trim()
    if (Ensure-Milestone -Milestone $milestone) {
      $milestoneArgs = @("--milestone", $milestone)
    }
  }

  # Create the issue
  $createArgs = @("issue", "create", "--repo", $Repo, "--title", $row.Title, "--body", $row.Body) + $labelArgs + $milestoneArgs
  $issueOutput = gh @createArgs
  if (-not $issueOutput) {
    Write-Error "Failed to create issue: $($row.Title)"
    continue
  }
  $issueNumber = $null
  $issueOutputLines = $issueOutput -split '\r?\n'
  $lastLine = ($issueOutputLines | Where-Object { $_ -match '\S' } | Select-Object -Last 1)
  if ($lastLine -match '/issues/(\d+)$') {
    $issueNumber = [int]$Matches[1]
  } elseif ($lastLine -match '(\d+)$') {
    $issueNumber = [int]$Matches[1]
  }
  if (-not $issueNumber) {
    Write-Error "Created issue but could not determine number. Output: $issueOutput"
    continue
  }
  $titleToNumber[$row.Title] = [int]$issueNumber
  Write-Host "Created #$issueNumber - $($row.Title)"
}

# Second pass: add dependency comments
foreach ($row in $rows) {
  $depends = $row."Depends On (titles)"
  if (-not $depends) { continue }
  if (-not $titleToNumber.ContainsKey($row.Title)) {
    Write-Host ("Skipping dependency comment for '{0}' because no issue number was recorded." -f $row.Title)
    continue
  }
  $current = $titleToNumber[$row.Title]
  $depTitles = $depends.Split(";") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
  $depNumbers = @()
  foreach ($t in $depTitles) {
    if ($titleToNumber.ContainsKey($t)) { $depNumbers += "#$($titleToNumber[$t])" }
    else { $depNumbers += $t } # fallback to title if number unknown
  }
  $comment = "Depends on: " + ($depNumbers -join ", ")
  gh issue comment $current --repo $Repo --body $comment | Out-Null
  Write-Host ("Added dependency comment to #{0}: {1}" -f $current, $comment)
}
