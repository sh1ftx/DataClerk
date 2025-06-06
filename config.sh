#!/bin/bash

# ==============================================================================
# CONFIG.SH - INSTALADOR MULTIPLATAFORMA E ROBUSTO PARA SEU PROJETO PYTHON
# ==============================================================================

set -e

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/install.log"
exec > >(tee -i "$LOGFILE")
exec 2>&1

function show_banner() {
cat << "EOF"
   ____        _        __  __                  
  / ___|  ___ | |_ __ _|  \/  | ___ _ __  _   _ 
  \___ \ / _ \| __/ _` | |\/| |/ _ \ '_ \| | | |
   ___) | (_) | || (_| | |  | |  __/ | | | |_| |
  |____/ \___/ \__\__,_|_|  |_|\___|_| |_|\__, |
                                          |___/ 
Instalador automático do ambiente Python com VENV.

👨‍💻 Desenvolvido por: Kayki Ivan (Sh1ft)
EOF
}

function print_header() {
  echo -e "\n\033[1;34m================================================================================"
  echo -e "        $1"
  echo -e "================================================================================\033[0m"
}

function print_step() {
  echo -e "\033[1;32m[PASSO] $1\033[0m"
}

function print_warn() {
  echo -e "\033[1;33m[AVISO] $1\033[0m"
}

function print_error() {
  echo -e "\033[1;31m[ERRO] $1\033[0m"
}

function ask_user() {
  read -p "$1 (s/n): " choice
  case "$choice" in
    s|S ) return 0 ;;
    n|N ) return 1 ;;
    * ) echo "Opção inválida." && ask_user "$1" ;;
  esac
}

function check_command() {
  if ! command -v "$1" &> /dev/null; then
    return 1
  fi
  return 0
}

# ========== INÍCIO ==========
show_banner

print_header "Detectando Sistema Operacional..."

OS=""
PM=""

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  if [ -f /etc/debian_version ]; then
    OS="debian"
    PM="sudo apt"
  elif [ -f /etc/arch-release ]; then
    OS="arch"
    PM="sudo pacman -Sy"
  else
    print_error "Distribuição Linux não suportada automaticamente."
    exit 1
  fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macos"
  PM="brew"
elif grep -qi microsoft /proc/version 2>/dev/null; then
  OS="wsl"
  PM="sudo apt"
else
  print_error "Sistema operacional não suportado: $OSTYPE"
  exit 1
fi

echo "Sistema detectado: $OS"

print_header "Verificando e instalando Python3..."

if ! check_command python3; then
  print_warn "Python3 não encontrado."
  if ask_user "Deseja instalar o Python3 agora?"; then
    case $OS in
      debian|wsl)
        $PM update -y
        $PM install python3 python3-pip python3-venv -y
        ;;
      arch)
        $PM python python-pip python-virtualenv --noconfirm
        ;;
      macos)
        $PM install python
        ;;
    esac
  else
    print_error "Python é obrigatório para continuar."
    exit 1
  fi
else
  echo "Python3 já está instalado."
fi

print_header "Criando ambiente virtual 'configs'..."

if [ ! -d "configs" ]; then
  python3 -m venv configs
  echo "Ambiente virtual criado."
fi

print_step "Ativando ambiente virtual..."

# Ativação para diferentes plataformas
if [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "linux"* ]]; then
  source configs/bin/activate
elif [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "cygwin"* || "$OSTYPE" == "win32" ]]; then
  source configs/Scripts/activate
fi

print_step "Atualizando pip e instalando dependências..."

pip install --upgrade pip
pip install mysql-connector-python tabulate colorama

print_step "Executando o script src/main.py..."

if [ -f "src/main.py" ]; then
  python src/main.py
else
  print_error "Arquivo src/main.py não encontrado."
  exit 1
fi
