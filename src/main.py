import mysql.connector
from mysql.connector import errorcode
from getpass import getpass
from tabulate import tabulate
from colorama import init, Fore, Style
import datetime
import sys
import time
import os

init(autoreset=True)

LOG_FILE = "verificacao_loja.log"

# ─────────────────────────────────────────────────────────────────────────────
# Utilitários de Log e Impressão
# ─────────────────────────────────────────────────────────────────────────────

def log(msg, mode='a'):
    with open(LOG_FILE, mode, encoding='utf-8') as f:
        f.write(msg + "\n")

def print_log(msg, color=None):
    if color:
        print(color + msg + Style.RESET_ALL)
    else:
        print(msg)
    log(msg)

def banner(titulo, char='─', cor=Fore.MAGENTA):
    tamanho = 80
    linha = char * tamanho
    print_log(f"\n{cor}{linha}")
    print_log(f"{cor}{titulo.center(tamanho)}")
    print_log(f"{cor}{linha}{Style.RESET_ALL}\n")

def tempo_execucao(inicio):
    return f"{(time.time() - inicio):.3f}s"

def perguntar_sim_nao(pergunta):
    while True:
        resposta = input(f"{Fore.CYAN}{pergunta} (s/n): {Style.RESET_ALL}").strip().lower()
        if resposta in ['s', 'n']:
            return resposta == 's'

# ─────────────────────────────────────────────────────────────────────────────
# Conexão com Banco de Dados
# ─────────────────────────────────────────────────────────────────────────────

def conectar_mysql():
    print_log(f"Tentando conexão com o banco de dados 'loja'...", Fore.CYAN)
    log("", mode='w')  # limpa log
    senha = getpass(f"Digite a senha do MySQL root: ")

    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password=senha,
            database="loja",
            auth_plugin='mysql_native_password'
        )
        print_log(f"Conexão bem-sucedida.", Fore.GREEN)
        return conexao
    except mysql.connector.Error as err:
        print_log(f"Erro de conexão: {err}", Fore.RED)
        sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Verificações de Estrutura e Dados
# ─────────────────────────────────────────────────────────────────────────────

def verificar_tabela(cursor, tabela, colunas_esperadas):
    cursor.execute(f"SHOW TABLES LIKE '{tabela}'")
    if cursor.fetchone() is None:
        return {'existe': False}

    cursor.execute(f"DESCRIBE {tabela}")
    colunas = [row[0] for row in cursor.fetchall()]
    colunas_set = set(colunas)
    esperadas_set = set(colunas_esperadas)

    return {
        'existe': True,
        'colunas': colunas,
        'colunas_corretas': colunas_set == esperadas_set,
        'faltando': list(esperadas_set - colunas_set),
        'extras': list(colunas_set - esperadas_set)
    }

def mostrar_registros(cursor, tabela, limite=3):
    cursor.execute(f"SELECT * FROM {tabela} LIMIT {limite}")
    linhas = cursor.fetchall()
    if not linhas:
        return f"{Fore.YELLOW}(sem registros)"
    cursor.execute(f"DESCRIBE {tabela}")
    colunas = [row[0] for row in cursor.fetchall()]
    return tabulate(linhas, headers=colunas, tablefmt="fancy_grid")

def contar_registros(cursor, tabela):
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    return cursor.fetchone()[0]

# ─────────────────────────────────────────────────────────────────────────────
# Procedures, Functions e Relacionamentos
# ─────────────────────────────────────────────────────────────────────────────

def existe_routine(cursor, nome, tipo):
    tipo = tipo.upper()
    query = f"SHOW {tipo} STATUS WHERE Db = DATABASE() AND Name = %s"
    cursor.execute(query, (nome,))
    return cursor.fetchone() is not None

def executar_funcao(cursor, nome_func, pedido_id):
    try:
        cursor.execute(f"SELECT {nome_func}(%s)", (pedido_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        return f"Erro executando função: {e}"

def pegar_itens_pedido(cursor, pedido_id):
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = %s", (pedido_id,))
    linhas = cursor.fetchall()
    if not linhas:
        return f"{Fore.YELLOW}(pedido sem itens)"
    cursor.execute("DESCRIBE itens_pedido")
    colunas = [row[0] for row in cursor.fetchall()]
    return tabulate(linhas, headers=colunas, tablefmt="fancy_grid")

def validar_relacionamentos(cursor):
    consultas = [
        ("cliente_id em pedidos", """
            SELECT p.id AS pedido_id, p.cliente_id, c.id AS cliente_existente 
            FROM pedidos p LEFT JOIN clientes c ON p.cliente_id = c.id 
            WHERE c.id IS NULL
        """),
        ("pedido_id em itens_pedido", """
            SELECT i.id AS item_id, i.pedido_id, p.id AS pedido_existente
            FROM itens_pedido i LEFT JOIN pedidos p ON i.pedido_id = p.id 
            WHERE p.id IS NULL
        """),
        ("produto_id em itens_pedido", """
            SELECT i.id AS item_id, i.produto_id, pr.id AS produto_existente
            FROM itens_pedido i LEFT JOIN produtos pr ON i.produto_id = pr.id 
            WHERE pr.id IS NULL
        """)
    ]
    resultados = []
    for nome, query in consultas:
        cursor.execute(query)
        linhas = cursor.fetchall()
        ok = len(linhas) == 0
        resultados.append((nome, ok, linhas))
    return resultados

# ─────────────────────────────────────────────────────────────────────────────
# Procedimentos Dinâmicos
# ─────────────────────────────────────────────────────────────────────────────

def testar_procedures(cursor, conexao):
    cliente_id = 1
    data_hoje = datetime.date.today().strftime('%Y-%m-%d')

    print_log(f"- Executando 'criar_pedido' com cliente_id={cliente_id}...", Fore.CYAN)
    try:
        args = [cliente_id]
        cursor.callproc('criar_pedido', args)
        conexao.commit()
        print_log(f"  ✔ Pedido criado com sucesso.", Fore.GREEN)
    except Exception as e:
        print_log(f"  ✘ Erro ao criar pedido: {e}", Fore.RED)
        return

    # Recupera o id do pedido criado para usar nos testes
    cursor.execute("SELECT MAX(id) FROM pedidos WHERE cliente_id = %s", (cliente_id,))
    pedido_id = cursor.fetchone()[0]

    produto_id = 1
    qtd = 2

    print_log(f"- Adicionando item ao pedido_id={pedido_id}, produto_id={produto_id}, quantidade={qtd}...", Fore.CYAN)
    try:
        cursor.callproc('adicionar_item', [pedido_id, produto_id, qtd])
        conexao.commit()
        print_log(f"  ✔ Item adicionado com sucesso.", Fore.GREEN)
    except Exception as e:
        print_log(f"  ✘ Erro ao adicionar item: {e}", Fore.RED)

    # Mostrar itens do pedido criado
    print_log(f"\nItens atuais do pedido {pedido_id}:", Fore.MAGENTA)
    print_log(pegar_itens_pedido(cursor, pedido_id))

# ─────────────────────────────────────────────────────────────────────────────
# Execução Principal
# ─────────────────────────────────────────────────────────────────────────────

def main():
    inicio = time.time()
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    conexao = conectar_mysql()
    cursor = conexao.cursor()

    # ─ Questão 1 ─
    banner("Questão 1 - Verificação Estrutura e Dados", cor=Fore.BLUE)
    tabelas = {
        'clientes': ['id', 'nome', 'email'],
        'produtos': ['id', 'nome', 'preco', 'estoque'],
        'pedidos': ['id', 'cliente_id', 'data_pedido'],
        'itens_pedido': ['id', 'pedido_id', 'produto_id', 'quantidade']
    }
    estrutura_ok = True
    dados_ok = True

    for tabela, colunas in tabelas.items():
        resultado = verificar_tabela(cursor, tabela, colunas)
        if not resultado.get('existe'):
            print_log(f"Tabela '{tabela}' NÃO existe.", Fore.RED)
            estrutura_ok = False
            continue

        print_log(f"Tabela '{tabela}' encontrada.", Fore.GREEN)
        if resultado['colunas_corretas']:
            print_log(f"- Colunas OK: {', '.join(resultado['colunas'])}")
        else:
            estrutura_ok = False
            if resultado['faltando']:
                print_log(f"- Faltando colunas: {', '.join(resultado['faltando'])}", Fore.RED)
            if resultado['extras']:
                print_log(f"- Colunas extras: {', '.join(resultado['extras'])}", Fore.YELLOW)

        print_log(f"- Exemplos de registros:")
        print_log(mostrar_registros(cursor, tabela))
        total = contar_registros(cursor, tabela)
        if total < 3:
            print_log(f"- Atenção: menos de 3 registros ({total})", Fore.YELLOW)
            dados_ok = False
        else:
            print_log(f"- Total de registros: {total}", Fore.GREEN)

    if estrutura_ok and dados_ok:
        print_log(f"\n✔ Estrutura e dados verificados com sucesso.", Fore.GREEN)
    else:
        print_log(f"\n✘ Problemas detectados na Questão 1.", Fore.RED)

    # ─ Questão 2 ─
    banner("Questão 2 - Procedures e Function", cor=Fore.BLUE)
    rotinas = {
        'criar_pedido': 'PROCEDURE',
        'adicionar_item': 'PROCEDURE',
        'calcular_total_pedido': 'FUNCTION'
    }
    rotinas_ok = True

    for nome, tipo in rotinas.items():
        if existe_routine(cursor, nome, tipo):
            print_log(f"- {tipo} '{nome}' encontrada.", Fore.GREEN)
        else:
            print_log(f"- {tipo} '{nome}' NÃO encontrada.", Fore.RED)
            rotinas_ok = False

    if rotinas_ok:
        print_log(f"\n✔ Todas rotinas estão presentes.", Fore.GREEN)
        print_log(f"- Testando função 'calcular_total_pedido' com pedido_id=1")
        resultado = executar_funcao(cursor, 'calcular_total_pedido', 1)
        if isinstance(resultado, str):
            print_log(f"  ✘ {resultado}", Fore.RED)
        else:
            print_log(f"  ✔ Resultado: R$ {resultado:.2f}", Fore.GREEN)
            print_log(f"\nItens do pedido 1:")
            print_log(pegar_itens_pedido(cursor, 1))
    else:
        print_log(f"\n✘ Falha na verificação de rotinas. Encerrando.", Fore.RED)
        cursor.close()
        conexao.close()
        sys.exit(1)

    # ─ Questão 3 ─
    banner("Questão 3 - Integridade Referencial", cor=Fore.BLUE)
    integridade_ok = True

    print_log("Validação dos relacionamentos e integridade referencial:\n", Fore.CYAN)
    resultados_rel = validar_relacionamentos(cursor)

    for nome, ok, linhas in resultados_rel:
        if ok:
            print_log(f"- {nome}: {Fore.GREEN}OK{Style.RESET_ALL} (nenhum registro inválido)")
        else:
            integridade_ok = False
            print_log(f"- {nome}: {Fore.RED}ERRO{Style.RESET_ALL} - {len(linhas)} registro(s) inválido(s) encontrado(s)")
            print_log(tabulate(linhas, headers="keys", tablefmt="fancy_grid", showindex=False), Fore.YELLOW)

    if integridade_ok:
        print_log("\n✔ Integridade referencial validada com sucesso.", Fore.GREEN)
    else:
        print_log("\n✘ Problemas detectados na integridade referencial.", Fore.RED)

    # ─ Questão 4 ─
    banner("Questão 4 - Testes dinâmicos das procedures", cor=Fore.BLUE)
    testar_procedures(cursor, conexao)

    cursor.close()
    conexao.close()
    print_log(f"\nExecução finalizada em {tempo_execucao(inicio)}", Fore.MAGENTA)

if __name__ == "__main__":
    main()
