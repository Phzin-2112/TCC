import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'app.db')

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            manchete TEXT NOT NULL,
            imagem TEXT,
            data TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def carregar_usuarios():
    """
    Retorna dict compatível com uso atual: {username: {'password': '...'}, ...}
    """
    usuarios = {}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT username, password FROM users')
    for row in cur.fetchall():
        usuarios[row['username']] = {'password': row['password']}
    conn.close()
    return usuarios

def add_user(username, password):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                    (username, password, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return False
    conn.close()
    return True

def carregar_contatos():
    """
    Retorna estrutura antiga: { email: [ {nome,email,manchete,imagem,data}, ... ], ... }
    """
    contatos = {}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT nome, email, manchete, imagem, data FROM posts ORDER BY data DESC')
    for row in cur.fetchall():
        item = {
            'nome': row['nome'],
            'email': row['email'],
            'manchete': row['manchete'],
            'imagem': row['imagem'],
            'data': row['data']
        }
        contatos.setdefault(row['email'], []).append(item)
    conn.close()
    return contatos

# substituir salvar_usuarios e salvar_contatos por wrappers que usam o DB quando necessário
def salvar_usuarios(usuarios):
    # mantém compatibilidade (reescreve tabela: remove todos e insere novamente)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('DELETE FROM users')
    for username, info in usuarios.items():
        cur.execute('INSERT OR IGNORE INTO users (username, password, created_at) VALUES (?, ?, ?)',
                    (username, info.get('password', ''), info.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
    conn.commit()
    conn.close()

def salvar_contatos(contatos):
    # opcional: inserir todos os posts do dict no DB (use com cuidado para não duplicar)
    conn = get_conn()
    cur = conn.cursor()
    for email, lista in contatos.items():
        for item in lista:
            cur.execute('''
                INSERT INTO posts (nome, email, manchete, imagem, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (item.get('nome',''), email, item.get('manchete',''), item.get('imagem'), item.get('data', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
    conn.commit()
    conn.close()