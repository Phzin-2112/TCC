# ...existing code...
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort

from models import add_user, carregar_usuarios, init_db, get_conn, carregar_contatos

app = Flask(__name__)
app.secret_key = 'SPFC'

_db_initialized = False

def _ensure_posts_status_column():
    """
    Garante que a coluna `status` exista na tabela posts.
    Se não existir, cria com valor padrão 'pendente'.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(posts)")
    cols = [r['name'] for r in cur.fetchall()]
    if 'status' not in cols:
        cur.execute("ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'pendente'")
        conn.commit()
    conn.close()

@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        try:
            _ensure_posts_status_column()
        except Exception:
            app.logger.exception("Erro ao garantir coluna status na tabela posts")
        _db_initialized = True

# ---------------------------
# Rotas de autenticação
# ---------------------------
@app.route('/')
def login_page():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    app.logger.debug("HEADERS: %s", dict(request.headers))
    app.logger.debug("FORM keys: %s", list(request.form.keys()))
    app.logger.debug("FORM data: %s", request.form.to_dict())

    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    app.logger.debug("POST /login username=%s", username)

    # Usuario do Admin
    if username == 'admin' and password == 'senha123':
        session['username'] = username
        session.permanent = True
        app.logger.debug("admin logged in, session keys=%s", list(session.keys()))
        flash('Login de admin efetuado com sucesso!', 'success')
        return redirect(url_for('admin'))

    usuarios = carregar_usuarios()
    user = usuarios.get(username)
    if user and user.get('password') == password:
        session['username'] = username
        session.permanent = True
        app.logger.debug("user logged in, session keys=%s", list(session.keys()))
        flash('Login efetuado com sucesso!', 'success')
        return redirect(url_for('loading'))

    app.logger.debug("login failed for %s", username)
    flash('Usuário ou senha incorretos!', 'danger')
    return redirect(url_for('login_page'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            flash('Preencha usuário e senha.', 'warning')
            return render_template('register.html')

        if add_user(username, password):
            flash('Cadastro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login_page'))
        else:
            flash('Usuário já existe!', 'warning')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login_page'))

# ---------------------------
# Telas utilitárias
# ---------------------------
@app.route('/loading')
def loading():
    app.logger.debug("GET /loading session: %s", dict(session))
    if 'username' in session:
        return render_template('loading.html')
    return redirect(url_for('login_page'))

@app.route('/index')
def index():
    if 'username' in session:
        contatos = listar_posts()
        return render_template('index.html', username=session['username'], contatos=contatos)
    flash('Faça login primeiro!', 'warning')
    return redirect(url_for('login_page'))

# ---------------------------
# Banco / posts helpers
# ---------------------------
def listar_posts():
    """
    Retorna dict agrupado por email: { email: [ {id,nome,email,manchete,imagem,data,status}, ... ], ... }
    """
    contatos = {}
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, nome, email, manchete, imagem, data, status FROM posts ORDER BY data DESC')
    rows = cur.fetchall()
    for row in rows:
        # sqlite3.Row não tem .get, então trata de forma segura
        status = row['status'] if (isinstance(row, dict) or hasattr(row, '__getitem__')) else (row.get('status') if hasattr(row, 'get') else 'pendente')
        item = {
            'id': row['id'],
            'nome': row['nome'],
            'email': row['email'],
            'manchete': row['manchete'],
            'imagem': row['imagem'],
            'data': row['data'],
            'status': status
        }
        contatos.setdefault(row['email'], []).append(item)
    conn.close()
    return contatos

def listar_posts_flat():
    """
    Retorna lista de posts ordenada por data decrescente.
    """
    posts = []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, nome, email, manchete, imagem, data, status FROM posts ORDER BY data DESC')
    rows = cur.fetchall()
    for row in rows:
        status = row['status'] if (isinstance(row, dict) or hasattr(row, '__getitem__')) else (row.get('status') if hasattr(row, 'get') else 'pendente')
        posts.append({
            'id': row['id'],
            'nome': row['nome'],
            'email': row['email'],
            'manchete': row['manchete'],
            'imagem': row['imagem'],
            'data': row['data'],
            'status': status
        })
    conn.close()
    return posts

def get_post(post_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, nome, email, manchete, imagem, data, status FROM posts WHERE id = ?', (post_id,))
    row = cur.fetchone()
    conn.close()
    return row

# ---------------------------
# Formulário de post (criar / atualizar)
# ---------------------------
@app.route('/post')
def post():
    if 'username' not in session:
        flash('Faça login primeiro!', 'warning')
        return redirect(url_for('login_page'))
    # renderiza formulário vazio para criação, passa lista de posts para mostrar lista no template
    posts = listar_posts_flat()
    return render_template('post.html', post=None, posts=posts)

@app.route('/enviar_contato', methods=['POST'])
def enviar_contato():
    if 'username' not in session:
        flash('Faça login para postar.', 'warning')
        return redirect(url_for('login_page'))

    try:
        post_id = request.form.get('post_id')
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        manchete = request.form.get('manchete', '').strip()
        imagem = request.form.get('imagem', '').strip() or None

        if not nome or not email or not manchete:
            flash('Por favor, preencha nome, e-mail e manchete.', 'warning')
            return redirect(url_for('post'))

        conn = get_conn()
        cur = conn.cursor()
        data_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if post_id:
            # manter status atual
            cur.execute('SELECT status FROM posts WHERE id = ?', (post_id,))
            row = cur.fetchone()
            status = row['status'] if row and (isinstance(row, dict) or hasattr(row, '__getitem__')) else (row.get('status') if row and hasattr(row, 'get') else 'pendente')
            cur.execute('''
                UPDATE posts
                SET nome = ?, email = ?, manchete = ?, imagem = ?, data = ?, status = ?
                WHERE id = ?
            ''', (nome, email, manchete, imagem, data_str, status, post_id))
            flash('Publicação atualizada com sucesso!', 'success')
        else:
            status = 'pendente'
            cur.execute('''
                INSERT INTO posts (nome, email, manchete, imagem, data, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, email, manchete, imagem, data_str, status))
            flash('Publicação adicionada com sucesso!', 'success')

        conn.commit()
        conn.close()
        return redirect(url_for('posts_list'))

    except Exception as e:
        app.logger.exception("Erro ao inserir/atualizar post")
        flash(f'Erro ao enviar publicação: {e}', 'danger')
        return redirect(url_for('post'))

# ---------------------------
# Editar / Excluir posts
# ---------------------------
@app.route('/post/<int:post_id>/edit')
def edit_post(post_id):
    if 'username' not in session:
        flash('Faça login primeiro!', 'warning')
        return redirect(url_for('login_page'))

    row = get_post(post_id)
    if not row:
        flash('Post não encontrado.', 'danger')
        return redirect(url_for('posts_list'))

    post = {
        'id': row['id'],
        'nome': row['nome'],
        'email': row['email'],
        'manchete': row['manchete'],
        'imagem': row['imagem'],
        'data': row['data'],
        'status': row['status'] if (isinstance(row, dict) or hasattr(row, '__getitem__')) else (row.get('status') if hasattr(row, 'get') else 'pendente')
    }
    posts = listar_posts_flat()
    return render_template('post.html', post=post, posts=posts)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'username' not in session:
        flash('Faça login primeiro!', 'warning')
        return redirect(url_for('login_page'))

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
        conn.close()
        flash('Post excluído com sucesso.', 'success')
    except Exception as e:
        app.logger.exception("Erro ao excluir post")
        flash(f'Erro ao excluir: {e}', 'danger')

    return redirect(request.referrer or url_for('posts_list'))

# ---------------------------
# Alterar status do post
# ---------------------------
@app.route('/post/<int:post_id>/status', methods=['POST'])
def set_status(post_id):
    if 'username' not in session:
        flash('Faça login primeiro!', 'warning')
        return redirect(url_for('login_page'))

    # somente admin pode alterar status
    if session.get('username') != 'admin':
        flash('Apenas admin pode alterar status.', 'danger')
        return redirect(request.referrer or url_for('posts_list'))

    status = (request.form.get('status') or 'pendente').lower()
    if status not in ('aprovado', 'reprovado', 'pendente'):
        flash('Status inválido.', 'warning')
        return redirect(request.referrer or url_for('posts_list'))

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('UPDATE posts SET status = ? WHERE id = ?', (status, post_id))
        conn.commit()
        conn.close()
        flash('Status atualizado.', 'success')
    except Exception as e:
        app.logger.exception("Erro ao atualizar status")
        flash(f'Erro ao atualizar status: {e}', 'danger')

    # volta para a página anterior (admin ou lista), evita TemplateNotFound se template faltando
    return redirect(request.referrer or url_for('posts_list'))

# ---------------------------
# Lista de posts e exclusão de antigos
# ---------------------------
@app.route('/posts')
def posts_list():
    if 'username' not in session:
        flash('Faça login primeiro!', 'warning')
        return redirect(url_for('login_page'))
    posts = listar_posts_flat()
    return render_template('post.html', posts=posts, username=session.get('username'))

@app.route('/delete_old_posts', methods=['POST'])
def delete_old_posts():
    if 'username' not in session:
        flash('Faça login primeiro!', 'warning')
        return redirect(url_for('login_page'))

    # apenas admin pode executar exclusão em massa
    if session.get('username') != 'admin':
        flash('Apenas admin pode excluir posts antigos em massa.', 'danger')
        return redirect(url_for('posts_list'))

    try:
        days = int(request.form.get('days', '30'))
    except ValueError:
        days = 30

    cutoff = datetime.now() - timedelta(days=days)
    cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM posts WHERE data < ?', (cutoff_str,))
        deleted = cur.rowcount
        conn.commit()
        conn.close()
        flash(f'{deleted} posts com mais de {days} dias excluídos.', 'success')
    except Exception as e:
        app.logger.exception("Erro ao excluir posts antigos")
        flash(f'Erro ao excluir posts antigos: {e}', 'danger')

    return redirect(url_for('posts_list'))

# ---------------------------
# Admin
# ---------------------------
@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        flash('Acesso negado! Apenas admin pode acessar.', 'danger')
        return redirect(url_for('index'))
    contatos = listar_posts()
    return render_template('admin.html', contatos=contatos)

# ---------------------------
# API de exemplo
# ---------------------------
@app.route('/api/dados')
def dados():
    return jsonify({
        'nome': 'Pedro Pizzas',
        'fundado': 2024,
        'dono': 'Mestre dos Magos'
    })

# ---------------------------
# Rodar o app
# ---------------------------
if __name__ == '__main__':
    init_db()
    # garantir coluna status também ao rodar direto
    try:
        _ensure_posts_status_column()
    except Exception:
        app.logger.exception("Erro ao garantir coluna status no startup")
    app.run(debug=True)
# ...existing code...