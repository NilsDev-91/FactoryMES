$path = 'c:\Users\Nilsg\.gemini\antigravity\mcp_config.json'
$config = Get-Content $path | ConvertFrom-Json

# Construct the new context7 server
$newServer = @{
    command = 'npx'
    args = @(
        '-y',
        '@upstash/context7-mcp',
        '--api-key',
        'ctx7sk-38609c66-8630-4f19-842d-1eb6a68602bd'
    )
}

# Add or update the context7 server
$config.mcpServers.context7 = $newServer

# Optional: Remote the old upstash-mcp-server if it exists, as it was likely a fragment-based guess
if ($config.mcpServers.'upstash-mcp-server') {
    $config.mcpServers.PSObject.Properties.Remove('upstash-mcp-server')
}

$config | ConvertTo-Json -Depth 10 | Set-Content -Path $path -Encoding utf8
