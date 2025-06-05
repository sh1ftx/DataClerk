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

def conectar_mysql():
    print_log(f"{Fore.CYAN}🔐 Tentando conexão com MySQL database 'loja'...{Style.RESET_ALL}")
    log("", mode='w')  # limpa o arquivo de log (modo write)

    senha = getpass(f"{Fore.YELLOW}Digite a senha do MySQL root: {Style.RESET_ALL}")
    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="root",
            password=senha,
            database="loja",
            auth_plugin='mysql_native_password'  # compatibilidade plugin
        )
        print_log(f"{Fore.GREEN}✅ Conexão ao MySQL realizada com sucesso.{Style.RESET_ALL}")
        return conexao
    except mysql.connector.Error as err:
        print_log(f"{Fore.RED}❌ Erro de conexão: {err}{Style.RESET_ALL}")
        sys.exit(1)

def verificar_tabela(cursor, tabela, colunas_esperadas):
    # Verifica se a tabela existe
    cursor.execute(f"SHOW TABLES LIKE '{tabela}'")
    existe = cursor.fetchone() is not None
    if not existe:
        return False, None

    # Verifica colunas da tabela
    cursor.execute(f"DESCRIBE {tabela}")
    colunas = [row[0] for row in cursor.fetchall()]
    colunas_set = set(colunas)
    colunas_esperadas_set = set(colunas_esperadas)

    colunas_corretas = colunas_set == colunas_esperadas_set
    colunas_faltando = colunas_esperadas_set - colunas_set
    colunas_extras = colunas_set - colunas_esperadas_set

    return {
        'existe': True,
        'colunas': colunas,
        'colunas_corretas': colunas_corretas,
        'faltando': list(colunas_faltando),
        'extras': list(colunas_extras)
    }

def mostrar_registros(cursor, tabela, limite=3):
    cursor.execute(f"SELECT * FROM {tabela} LIMIT {limite}")
    linhas = cursor.fetchall()
    if not linhas:
        return f"{Fore.YELLOW}(sem registros){Style.RESET_ALL}"
    cursor.execute(f"DESCRIBE {tabela}")
    colunas = [row[0] for row in cursor.fetchall()]
    return tabulate(linhas, headers=colunas, tablefmt="fancy_grid", numalign="right", stralign="left")

def contar_registros(cursor, tabela):
    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
    count = cursor.fetchone()[0]
    return count

def existe_routine(cursor, nome, tipo):
    if tipo == 'PROCEDURE':
        cursor.execute(f"SHOW PROCEDURE STATUS WHERE Db = DATABASE() AND Name = '{nome}'")
    elif tipo == 'FUNCTION':
        cursor.execute(f"SHOW FUNCTION STATUS WHERE Db = DATABASE() AND Name = '{nome}'")
    else:
        return False
    return cursor.fetchone() is not None

def executar_funcao(cursor, nome_func, pedido_id):
    try:
        cursor.execute(f"SELECT {nome_func}({pedido_id})")
        resultado = cursor.fetchone()
        if resultado:
            return resultado[0]
        else:
            return None
    except Exception as e:
        return f"Erro executando função: {e}"

def pegar_itens_pedido(cursor, pedido_id):
    cursor.execute("SELECT * FROM itens_pedido WHERE pedido_id = %s", (pedido_id,))
    linhas = cursor.fetchall()
    if not linhas:
        return f"{Fore.YELLOW}(pedido sem itens){Style.RESET_ALL}"
    cursor.execute("DESCRIBE itens_pedido")
    colunas = [row[0] for row in cursor.fetchall()]
    return tabulate(linhas, headers=colunas, tablefmt="fancy_grid", numalign="right", stralign="left")

def executar_procedure_criar_pedido(cursor, nome_proc, cliente_id, data_pedido):
    # Exemplo de chamada - adaptável conforme procedure criada
    try:
        cursor.callproc(nome_proc, [cliente_id, data_pedido, 0])  # supondo OUT no 3º param
        # para pegar OUT, pode usar cursor.stored_results() - depende da procedure real
        return True, "Procedure executada com sucesso"
    except Exception as e:
        return False, str(e)

def executar_procedure_adicionar_item(cursor, nome_proc, pedido_id, produto_id, quantidade):
    try:
        cursor.callproc(nome_proc, [pedido_id, produto_id, quantidade])
        return True, "Item adicionado com sucesso"
    except Exception as e:
        return False, str(e)

def validar_relacionamentos(cursor):
    """
    Valida integrity referencial básica
    (clientes.id -> pedidos.cliente_id, pedidos.id -> itens_pedido.pedido_id, produtos.id -> itens_pedido.produto_id)
    """
    rels = [
        {
            'nome': 'cliente_id em pedidos',
            'query': "SELECT COUNT(*) FROM pedidos p LEFT JOIN clientes c ON p.cliente_id = c.id WHERE c.id IS NULL"
        },
        {
            'nome': 'pedido_id em itens_pedido',
            'query': "SELECT COUNT(*) FROM itens_pedido i LEFT JOIN pedidos p ON i.pedido_id = p.id WHERE p.id IS NULL"
        },
        {
            'nome': 'produto_id em itens_pedido',
            'query': "SELECT COUNT(*) FROM itens_pedido i LEFT JOIN produtos pr ON i.produto_id = pr.id WHERE pr.id IS NULL"
        }
    ]
    resultados = []
    for r in rels:
        cursor.execute(r['query'])
        count = cursor.fetchone()[0]
        resultados.append((r['nome'], count == 0, count))
    return resultados

def tempo_execucao(inicio):
    fim = time.time()
    duracao = fim - inicio
    return f"{duracao:.3f}s"

def perguntar_sim_nao(pergunta):
    while True:
        resposta = input(f"{Fore.CYAN}{pergunta} (s/n): {Style.RESET_ALL}").strip().lower()
        if resposta in ['s', 'n']:
            return resposta == 's'

def main():
    inicio = time.time()
    # Limpa log no início
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    conexao = conectar_mysql()
    cursor = conexao.cursor()

    banner("Questão 1 - Verificação Estrutura e Dados", cor=Fore.BLUE)
    tabelas_esperadas = {
        'clientes': ['id', 'nome', 'email'],
        'produtos': ['id', 'nome', 'preco', 'estoque'],
        'pedidos': ['id', 'cliente_id', 'data_pedido'],
        'itens_pedido': ['id', 'pedido_id', 'produto_id', 'quantidade'],
    }

    q1_estrutura_ok = True
    q1_dados_ok = True

    for tabela, colunas in tabelas_esperadas.items():
        resultado = verificar_tabela(cursor, tabela, colunas)
        if not resultado['existe']:
            print_log(f"{Fore.RED}❌ Tabela '{tabela}' NÃO existe.{Style.RESET_ALL}")
            q1_estrutura_ok = False
            continue

        print_log(f"{Fore.GREEN}✅ Tabela '{tabela}' existe.{Style.RESET_ALL}")
        if resultado['colunas_corretas']:
            print_log(f"{Fore.GREEN}  Colunas estão corretas: {', '.join(resultado['colunas'])}")
        else:
            q1_estrutura_ok = False
            if resultado['faltando']:
                print_log(f"{Fore.RED}  Colunas faltando: {', '.join(resultado['faltando'])}")
            if resultado['extras']:
                print_log(f"{Fore.YELLOW}  Colunas extras: {', '.join(resultado['extras'])}")

        # Exibir alguns registros
        print_log(f"{Fore.CYAN}  Exemplos de registros na tabela '{tabela}':")
        exemplos = mostrar_registros(cursor, tabela)
        print_log(exemplos)

        # Verificar se há pelo menos 3 registros
        count = contar_registros(cursor, tabela)
        if count < 3:
            print_log(f"{Fore.YELLOW}⚠️ Atenção: tabela '{tabela}' possui menos de 3 registros ({count}).{Style.RESET_ALL}")
            q1_dados_ok = False
        else:
            print_log(f"{Fore.GREEN}  Tabela '{tabela}' tem {count} registros.{Style.RESET_ALL}")

    if q1_estrutura_ok and q1_dados_ok:
        print_log(f"\n{Fore.GREEN}✔️ Questão 1 concluída com sucesso: estrutura e dados corretos.{Style.RESET_ALL}")
    else:
        print_log(f"\n{Fore.RED}❌ Questão 1 encontrou problemas na estrutura ou dados.{Style.RESET_ALL}")

    banner("Questão 2 - Procedures e Function", cor=Fore.BLUE)
    procedimentos_esperados = {
        'criar_pedido': 'PROCEDURE',
        'adicionar_item': 'PROCEDURE',
        'calcular_total_pedido': 'FUNCTION'
    }

    q2_ok = True

    for nome, tipo in procedimentos_esperados.items():
        existe = existe_routine(cursor, nome, tipo)
        if existe:
            print_log(f"{Fore.GREEN}✅ {tipo} '{nome}' existe.{Style.RESET_ALL}")
        else:
            print_log(f"{Fore.RED}❌ {tipo} '{nome}' NÃO encontrada.{Style.RESET_ALL}")
            q2_ok = False

    if not q2_ok:
        print_log(f"{Fore.RED}❌ Questão 2 não passou por procedimentos ausentes.{Style.RESET_ALL}")
        cursor.close()
        conexao.close()
        sys.exit(1)

    # Teste prático da função calcular_total_pedido para pedido_id=1
    print_log(f"\n{Fore.CYAN}Testando função 'calcular_total_pedido' para pedido_id=1...")
    resultado_func = executar_funcao(cursor, 'calcular_total_pedido', 1)
    if resultado_func is None:
        print_log(f"{Fore.RED}Erro: função retornou NULL ou erro.{Style.RESET_ALL}")
        q2_ok = False
    elif isinstance(resultado_func, str) and resultado_func.startswith("Erro"):
        print_log(f"{Fore.RED}{resultado_func}{Style.RESET_ALL}")
        q2_ok = False
    else:
        print_log(f"{Fore.GREEN}Resultado: total do pedido_id=1 é {resultado_func:.2f}{Style.RESET_ALL}")

    # Exibir itens do pedido 1 para validação visual
    print_log(f"\n{Fore.CYAN}Itens do pedido_id=1 para validação:")
    print_log(pegar_itens_pedido(cursor, 1))

    banner("Questão 3 - Integridade Referencial e Relacionamentos", cor=Fore.BLUE)
    rel_results = validar_relacionamentos(cursor)
    rel_ok = True
    for nome_rel, ok, count in rel_results:
        if ok:
            print_log(f"{Fore.GREEN}✅ Integridade ok: {nome_rel}{Style.RESET_ALL}")
        else:
            print_log(f"{Fore.RED}❌ Integridade quebrada: {nome_rel} tem {count} registros inválidos.{Style.RESET_ALL}")
            rel_ok = False

    if rel_ok:
        print_log(f"{Fore.GREEN}✔️ Questão 3 concluída: integridade referencial está OK.{Style.RESET_ALL}")
    else:
        print_log(f"{Fore.RED}❌ Questão 3 encontrou problemas na integridade referencial.{Style.RESET_ALL}")

    banner("Questão 4 - Testes Dinâmicos de Procedures", cor=Fore.BLUE)
    # Exemplo simplificado, precisa adaptar procedure de criação e adição
    if perguntar_sim_nao("Deseja executar testes dinâmicos da procedure 'criar_pedido' e 'adicionar_item'?"):
        # Teste básico criar_pedido
        cliente_id_test = 1
        data_test = datetime.date.today().strftime("%Y-%m-%d")
        print_log(f"Executando procedure 'criar_pedido' com cliente_id={cliente_id_test} e data_pedido='{data_test}'")
        try:
            cursor.callproc('criar_pedido', [cliente_id_test, data_test, 0])  # 3º param OUT id_pedido
            # pegar OUT param
            for result in cursor.stored_results():
                print_log(f"Procedure result: {result.fetchall()}")
            conexao.commit()
            print_log(f"{Fore.GREEN}✅ Procedure 'criar_pedido' executada com sucesso.{Style.RESET_ALL}")
        except Exception as e:
            print_log(f"{Fore.RED}Erro executando 'criar_pedido': {e}{Style.RESET_ALL}")

        # Teste adicionar_item
        print_log(f"Tentando adicionar item no pedido recém criado...")
        try:
            pedido_id_test = 1  # para testes, usar 1 (ou capturar do OUT acima)
            produto_id_test = 1
            quantidade_test = 2
            cursor.callproc('adicionar_item', [pedido_id_test, produto_id_test, quantidade_test])
            conexao.commit()
            print_log(f"{Fore.GREEN}✅ Procedure 'adicionar_item' executada com sucesso.{Style.RESET_ALL}")
        except Exception as e:
            print_log(f"{Fore.RED}Erro executando 'adicionar_item': {e}{Style.RESET_ALL}")
    else:
        print_log("Testes dinâmicos ignorados pelo usuário.")

    cursor.close()
    conexao.close()
    duracao = tempo_execucao(inicio)
    banner(f"Verificação concluída em {duracao}", cor=Fore.GREEN)

if __name__ == "__main__":
    main()
