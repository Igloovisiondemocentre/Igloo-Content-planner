$workspace = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $workspace 'src'
$python = 'C:\Users\AshtonKehinde\AppData\Local\Programs\Python\Python312\python.exe'
Set-Location $workspace
& $python -m igloo_experience_builder builder-ui --host 127.0.0.1 --port 8765 --no-browser
