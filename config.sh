#!/bin/bash
set -e

MYSQL_USER="root"
MYSQL_PASS="@"
DB_NAME="loja"

# Detectar cliente MySQL/MariaDB
if command -v mysql >/dev/null 2>&1; then
    MYSQL_CMD="mysql"
elif command -v mariadb >/dev/null 2>&1; then
    MYSQL_CMD="mariadb"
else
    echo "❌ Nenhum cliente MySQL/MariaDB encontrado."
    exit 1
fi

run_sql_sudo() {
  local sql="$1"
  local tmpfile
  tmpfile=$(mktemp)
  echo "$sql" > "$tmpfile"
  sudo $MYSQL_CMD -u "$MYSQL_USER" --password="$MYSQL_PASS" -e "source $tmpfile"
  rm -f "$tmpfile"
}

run_sql_direct() {
  echo "$1" | $MYSQL_CMD -u "$MYSQL_USER" --password="$MYSQL_PASS"
}

echo "🔍 Testando conexão com banco de dados..."
if run_sql_direct "SELECT 1;" >/dev/null 2>&1; then
  echo "✅ Conexão OK."
else
  echo "❌ Falha na conexão com o banco de dados."
  echo "   ➤ Tente executar o script com sudo, ou configure o acesso root corretamente."
  exit 1
fi

echo "🔴 Apagando banco '$DB_NAME' (se existir)..."
if ! run_sql_direct "DROP DATABASE IF EXISTS $DB_NAME;" >/dev/null 2>&1; then
  echo "⚠️ Comando direto falhou, usando sudo."
  run_sql_sudo "DROP DATABASE IF EXISTS $DB_NAME;"
fi

echo "🟢 Criando banco '$DB_NAME'..."
if ! run_sql_direct "CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" >/dev/null 2>&1; then
  echo "⚠️ Comando direto falhou, usando sudo."
  run_sql_sudo "CREATE DATABASE $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
fi

# SQL para criação das tabelas, dados e procedures
SQL_COMMANDS=$(cat <<'SQL_EOF'
-- Tabelas
CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    preco DECIMAL(10,2) NOT NULL,
    estoque INT NOT NULL
);
CREATE TABLE pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT NOT NULL,
    data_pedido DATE NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
);
CREATE TABLE itens_pedido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE
);

-- Dados iniciais
INSERT INTO clientes (nome, email) VALUES
('Alice Souza', 'alice@email.com'),
('Bruno Lima', 'bruno@email.com'),
('Carla Dias', 'carla@email.com');

INSERT INTO produtos (nome, preco, estoque) VALUES
('Teclado Gamer', 150.00, 18),
('Mouse Óptico', 80.00, 49),
('Monitor LED', 750.00, 10);

-- Função
DROP FUNCTION IF EXISTS calcular_total_pedido;
DELIMITER $$
CREATE FUNCTION calcular_total_pedido(p_pedido_id INT) RETURNS DECIMAL(10,2)
DETERMINISTIC
BEGIN
    DECLARE total DECIMAL(10,2);
    SELECT SUM(p.preco * ip.quantidade) INTO total
    FROM itens_pedido ip
    JOIN produtos p ON p.id = ip.produto_id
    WHERE ip.pedido_id = p_pedido_id;
    RETURN IFNULL(total, 0);
END$$
DELIMITER ;

-- Procedures
DROP PROCEDURE IF EXISTS criar_pedido;
DELIMITER $$
CREATE PROCEDURE criar_pedido(
    IN p_cliente_id INT,
    IN p_data_pedido DATE,
    OUT p_pedido_id INT
)
BEGIN
    INSERT INTO pedidos(cliente_id, data_pedido)
    VALUES (p_cliente_id, p_data_pedido);
    SET p_pedido_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS adicionar_item;
DELIMITER $$
CREATE PROCEDURE adicionar_item(
    IN p_pedido_id INT,
    IN p_produto_id INT,
    IN p_quantidade INT
)
BEGIN
    DECLARE estoque_atual INT;
    SELECT estoque INTO estoque_atual FROM produtos WHERE id = p_produto_id;
    IF estoque_atual >= p_quantidade THEN
        INSERT INTO itens_pedido(pedido_id, produto_id, quantidade)
        VALUES (p_pedido_id, p_produto_id, p_quantidade);
        UPDATE produtos SET estoque = estoque - p_quantidade WHERE id = p_produto_id;
    ELSE
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Estoque insuficiente para o produto.';
    END IF;
END$$
DELIMITER ;

-- Pedidos e Itens
CALL criar_pedido(1, '2025-06-05', @p1);
CALL criar_pedido(2, '2025-06-06', @p2);
CALL criar_pedido(3, '2025-06-07', @p3);

CALL adicionar_item(@p1, 1, 2);
CALL adicionar_item(@p1, 2, 1);
CALL adicionar_item(@p2, 2, 3);
CALL adicionar_item(@p3, 3, 1);
CALL adicionar_item(@p3, 1, 1);
SQL_EOF
)

echo "🟢 Criando tabelas, procedures e inserindo dados..."

if ! echo "$SQL_COMMANDS" | $MYSQL_CMD -u "$MYSQL_USER" --password="$MYSQL_PASS" "$DB_NAME"; then
  echo "⚠️ Comando direto falhou, usando sudo."
  local tmpfile=$(mktemp)
  echo "$SQL_COMMANDS" > "$tmpfile"
  sudo $MYSQL_CMD -u "$MYSQL_USER" --password="$MYSQL_PASS" "$DB_NAME" < "$tmpfile"
  rm -f "$tmpfile"
fi

echo "✅ Banco de dados e objetos criados e populados com sucesso."

echo "🔧 Criando ambiente virtual Python..."
python3 -m venv venv

echo "🟢 Ativando ambiente virtual..."
source venv/bin/activate

echo "🛠 Instalando bibliotecas necessárias..."
pip install --upgrade pip
pip install mysql-connector-python colorama prettytable tabulate

echo "🟢 Executando script Python src/main.py"
if [ -f "src/main.py" ]; then
    python src/main.py
else
    echo "⚠️ Arquivo src/main.py não encontrado. Pulei essa etapa."
fi

echo "✅ Processo finalizado com sucesso."
