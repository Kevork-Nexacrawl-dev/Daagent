from tools.native.execute_powershell import execute_powershell

result = execute_powershell('Write-Host "Hello from PowerShell!"')
print(result)