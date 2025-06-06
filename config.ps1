# ==============================================================================
# CONFIG.PS1 - INSTALADOR AUTOMÁTICO PARA WINDOWS - Kayki Ivan (Sh1ft)
# ==============================================================================

$ErrorActionPreference = "Stop"
$LogPath = "logs\install.log"
New-Item -ItemType Directory -Force -Path "logs" | Out-Null
Start-Transcript -Path $LogPath -Append

function Show-Banner {
@"
   ____        _        __  __                  
  / ___|  ___ | |_ __ _|  \/  | ___ _ __  _   _ 
  \___ \ / _ \| __/ _` | |\/| |/ _ \ '_ \| | | |
   ___) | (_) | || (_| | |  | |  __/ | | | |_| |
  |____/ \___/ \__\__,_|_|  |_|\___|_| |_|\__, |
                                          |___/ 
Instalador automático do ambiente Python com VENV.

👨‍💻 Desenvolvido por: Kayki Ivan (Sh1ft)
"@
}

function Print-Header($msg) {
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "        $msg" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
}

function Print-Step($msg) {
    Write-Host "[PASSO] $msg" -ForegroundColor Green
}

function Print-Warn($msg) {
    Write-Host "[AVISO] $msg" -ForegroundColor Yellow
}

function Print-Error($msg) {
    Write-Host "[ERRO] $msg" -ForegroundColor Red
}

function Ask-User($question) {
    do {
        $resp = Read-Host "$question (s/n)"
    } while ($resp -notin @('s','S','n','N'))

    return $resp -in @('s', 'S')
}

function Check-Command($cmd) {
    $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

Show-Banner

Print-Header "Verificando instalação do Python..."

if (-not (Check-Command "python")) {
    Print-Warn "Python não está instalado."
    if (Ask-User "Deseja instalar o Python automaticamente?") {
        Print-Step "Baixando instalador..."
        $url = "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe"
        $exe = "$env:TEMP\python_installer.exe"
        Invoke-WebRequest $url -OutFile $exe

        Print-Step "Executando instalador..."
        Start-Process $exe -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait

        Remove-Item $exe
    } else {
        Print-Error "Instalação abortada. Python é necessário."
        Stop-Transcript
        exit 1
    }
} else {
    Write-Host "Python já está instalado."
}

Print-Header "Criando ambiente virtual 'configs'..."

if (-not (Test-Path "configs")) {
    python -m venv configs
    Print-Step "Ambiente virtual criado."
}

Print-Step "Ativando ambiente virtual..."
& .\configs\Scripts\Activate.ps1

Print-Step "Atualizando pip..."
pip install --upgrade pip

Print-Step "Instalando bibliotecas do projeto..."
pip install mysql-connector-python tabulate colorama

Print-Header "Executando o script src\main.py..."

if (Test-Path "src\main.py") {
    python src\main.py
} else {
    Print-Error "Arquivo src\main.py não encontrado."
    Stop-Transcript
    exit 1
}

Stop-Transcript
