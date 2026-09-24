param(
    [string]$NodeMap = "$PSScriptRoot/node-map.json",
    [string]$OutputPath = "$PSScriptRoot/Feeder01.tags.json"
)
$ErrorActionPreference = 'Stop'
$symbolPath = Join-Path $PSScriptRoot '../plc/symbols.xml'
[xml]$symbols = Get-Content -LiteralPath $symbolPath -Raw
$leaves = @($symbols.SelectNodes("//*[local-name()='Node' and @type='T_BOOL']"))
$map = Get-Content -LiteralPath $NodeMap -Raw | ConvertFrom-Json
$names = @($map.PSObject.Properties.Name)
$expected = @($leaves | ForEach-Object { $_.name })
if ($expected.Count -ne 13) { throw 'Expected exactly 13 published Boolean symbols.' }
if (@(Compare-Object $expected $names).Count) { throw 'Node map must contain exactly the published symbol names.' }
$paths = @()
$tags = foreach ($symbol in $leaves) {
    $path = $map.($symbol.name)
    if ($path -isnot [string] -or [string]::IsNullOrWhiteSpace($path) -or $path -match 'REPLACE|TODO|PLACEHOLDER') {
        throw "Missing browsed OPC item path for $($symbol.name). No import generated."
    }
    $paths += $path
    [ordered]@{
        name = [string]$symbol.name
        tagType = 'AtomicTag'
        dataType = 'Boolean'
        valueSource = 'opc'
        opcServer = 'CODESYS_Local'
        opcItemPath = $path
        readOnly = $true
        documentation = "Local feeder lab. PLC access: $($symbol.access). Initial integration is monitoring only."
    }
}
if (@($paths | Sort-Object -Unique).Count -ne 13) { throw 'Each symbol must have a distinct browsed OPC item path.' }
$package = @{ tags = @(@{ name = 'Feeder01'; tagType = 'Folder'; tags = @($tags) }) }
$package | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
Write-Output "Created monitoring import with 13 Boolean OPC tags: $OutputPath"
