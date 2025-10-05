# Prevent CRLF/mixed endings on non-PS1 files
$bad = git ls-files --eol | Select-String '^(?!.*\.ps1$).*w/(crlf|mixed)'
if ($bad) {
  Write-Error "Non-PS1 file has CRLF or mixed line endings:`n$($bad -join "`n")"
  exit 1
}

