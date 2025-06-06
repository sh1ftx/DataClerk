```
  ____        _         ____ _           _    
 |  _ \  __ _| |_ __ _ / ___| | ___ _ __| | __
 | | | |/ _` | __/ _` | |   | |/ _ \ '__| |/ /
 | |_| | (_| | || (_| | |___| |  __/ |  |   < 
 |____/ \__,_|\__\__,_|\____|_|\___|_|  |_|\_\
```

---

> **Trabalho da disciplina:** Banco de Dados II  
> **Curso:** Analise e Desenvolvimento de Sistemas - Faculdade  
> **Autor:** Kayki Ivan (Sh1ft)  

---

## 📌 Descrição

- Checagem da existência de tabelas obrigatórias;
- Verificação da presença de dados em tabelas essenciais;
- Validação da criação de **procedures** e **funções**;
- Conferência de **chaves estrangeiras** e integridade referencial;
- Execução de scripts Python com ambiente virtual isolado.

O projeto inclui scripts automatizados de instalação tanto para **Linux/macOS (Bash)** quanto **Windows (PowerShell)**.

## ⚙️ Pré-requisitos

- Git
- MySQL Server
- Python 3.10+ (será instalado automaticamente se necessário)
- Acesso à internet para baixar dependências

## 🚀 Como clonar o projeto

```bash
git clone https://github.com/sh1ftx/DataClerk.git
cd DataClerk
```

## 💻 Executar no Linux/macOS

O script `config.sh` detecta a distribuição, instala o Python (se necessário), cria um ambiente virtual `configs`, instala as bibliotecas e executa o script principal.

```bash
chmod +x config.sh
./config.sh
```

## 🪟 Executar no Windows

O script `config.ps1` faz as mesmas etapas que a versão Linux: instala o Python automaticamente, cria o ambiente virtual `configs`, instala as bibliotecas e roda `src/main.py`.

1. Abra o PowerShell como Administrador
2. Execute os comandos:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\config.ps1
```

## 📂 Estrutura esperada

```ini
DataClerk/
├── config.sh           # Instalador para Linux/macOS
├── config.ps1          # Instalador para Windows
├── requirements.txt    # Bibliotecas necessárias
├── src/
│   └── main.py         # Script principal de verificação
├── logs/               # Logs da instalação
├── configs/            # Ambiente virtual (gerado)
└── README.md           # Este arquivo
```

## 📦 Bibliotecas Utilizadas

- `mysql-connector-python`
- `tabulate`
- `colorama`

## 📃 Licença

Este projeto é apenas para fins **educacionais**.  
Não possui licença de uso comercial.

---
