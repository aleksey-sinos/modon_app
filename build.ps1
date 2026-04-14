# Load secrets from modon/.env into the current shell session,
# then run docker compose build + up so build args are available.

Get-Content modon/.env | Where-Object { $_ -match '^\s*[^#]\S+=\S' } | ForEach-Object {
    $parts = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
}

docker compose down
docker compose build
docker compose up -d
