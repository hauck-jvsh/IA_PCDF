param(
    [string]$IpedDir = 'D:\IPED-4.3.1_and_java_plugins\iped-4.3.1',
    [string]$Caso = 'D:\iped_mcp\caso_sintetico',
    [ValidateSet('0','1')][string]$PermitirMarcadores = '1'
)
$ErrorActionPreference = 'Stop'
$env:IPED_HOME = $IpedDir
$env:JAVA_HOME = Join-Path $IpedDir 'jre'
$env:IPED_CASE = $Caso
$env:IPED_CASE_LABEL = 'AURORA_SINTETICO'
$env:IPED_ALLOW_BOOKMARK_WRITE = $PermitirMarcadores
$env:PATH = "$env:JAVA_HOME\bin;$env:JAVA_HOME\bin\server;$env:PATH"
foreach ($arquivo in @("$env:IPED_HOME\iped.jar", "$env:JAVA_HOME\bin\server\jvm.dll")) {
    if (-not (Test-Path -LiteralPath $arquivo)) { throw "Arquivo necessário ausente: $arquivo" }
}
Write-Output 'Variáveis definidas nesta sessão. Inicie o cliente por este terminal.'
