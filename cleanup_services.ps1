
Write-Host "Restarting Docker Container..."
docker restart factory_db

Write-Host "Freeing ports 8000 (API) and 5173 (Frontend)..."
# Using npx kill-port to handle cross-platform port killing gracefully
cmd /c "npx -y kill-port 8000 5173"
Write-Host "Cleanup Complete."
