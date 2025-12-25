
Write-Host "Stopping FactoryOS Services..."

# 1. Kill Port 8000 (API)
$port8000 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($port8000) {
    Write-Host "Killing process on Port 8000 (PID: $($port8000.OwningProcess))"
    Stop-Process -Id $port8000.OwningProcess -Force -ErrorAction SilentlyContinue
}

# 2. Kill Port 5173 (Frontend)
$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Host "Killing process on Port 5173 (PID: $($port5173.OwningProcess))"
    Stop-Process -Id $port5173.OwningProcess -Force -ErrorAction SilentlyContinue
}

# 3. Kill main_daemon.py
$daemon = Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*main_daemon.py*' }
if ($daemon) {
    Write-Host "Killing main_daemon.py (PID: $($daemon.ProcessId))"
    Stop-Process -Id $daemon.ProcessId -Force -ErrorAction SilentlyContinue
}
    
Write-Host "Cleanup Complete."
