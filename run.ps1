param([ValidateSet('Start','Test','Browser','CheckExport')][string]$Mode='Start',[int]$Port=8530)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$configPath=Join-Path $PSScriptRoot 'runtime.local.json'
$config=if(Test-Path -LiteralPath $configPath){Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json}else{$null}
$pythonExe=if($config -and $config.python -and (Test-Path -LiteralPath $config.python)){$config.python}else{(Get-Command python).Source}
switch($Mode){
 'Start' { & $pythonExe server.py --port $Port }
 'Test' { & $pythonExe scripts/run_tests.py final }
 'Browser' { if(-not $config){throw '需要 runtime.local.json 配置 Node 与依赖路径。'}; & $config.node scripts/browser_engine_v3.mjs }
 'CheckExport' { & $pythonExe scripts/verify_real_export.py }
}
exit $LASTEXITCODE
