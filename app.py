import os
import shutil
import csv
from io import StringIO
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, Response
import psycopg2
import psycopg2.extras
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clima_positivo_segredo_super_seguro'

# Configuração da Base de Dados (Compatível com PostgreSQL do Supabase e fallback para SQLite local)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DB_NAME = 'stock_manager.db'

# Dicionário de Tradução (Português -> Francês)
FR_DICT = {
    'Controlo de Obra & Stock': 'Contrôle de Chantier & Stock',
    'Resumo': 'Résumé',
    'Estoque': 'Stock',
    'Movimentos': 'Mouvements',
    'Banco de Sobras': 'Banque d\'Excédents',
    'Obras': 'Chantiers',
    'Funcionários': 'Employés',
    'Sair': 'Déconnexion',
    'Gestão de Materiais e Excedentes': 'Gestion des Matériaux et Excédents',
    'Registar Saída': 'Enregistrer Sortie',
    'Registar Movimento': 'Enregistrer Mvt',
    'Exportar Excel': 'Exporter Excel',
    'Materiais': 'Matériaux',
    'Entradas Hoje': 'Entrées',
    'Saídas Hoje': 'Sorties',
    'Sobras Disp.': 'Excédents Disp.',
    'Últimos Movimentos': 'Derniers Mouvements',
    'Ver Todos': 'Voir Tout',
    'Tipo': 'Type',
    'Código': 'Code',
    'Material': 'Matériel',
    'Qtd': 'Qté',
    'Qtd Total': 'Qté Totale',
    'Funcionário': 'Employé',
    'Nenhum movimento registado.': 'Aucun mouvement enregistré.',
    'Banco de Sobras Ativas': 'Excédents Actifs',
    'Banco de Sobras Ativas (Soma Total)': 'Excédents Actifs (Somme Totale)',
    'Gerir Sobras': 'Gérer Excédents',
    'Local': 'Lieu',
    'Ação': 'Action',
    'Utilizar': 'Utiliser',
    'Nenhuma sobra disponível.': 'Aucun excédent disponible.',
    'Inventário de Estoque Atual': 'Inventaire de Stock',
    'Voltar': 'Retour',
    'Saldo en Tempo Real no Armazém': 'Solde en Temps Réel au Dépôt',
    'Quantidade em Estoque': 'Quantité en Stock',
    'Estado': 'État',
    'Estoque Baixo': 'Stock Faible',
    'Disponível': 'Disponible',
    'Nenhum material em estoque.': 'Aucun matériel en stock.',
    'Registo de Entradas e Saídas': 'Registre des Entrées et Sorties',
    'Mode Funcionário Ativo': 'Mode Employé Actif',
    'Novo Movimento de Material': 'Nouveau Mouvement de Matériel',
    'Tipo de Movimento': 'Type de Mouvement',
    'Entrada': 'Entrée',
    'Saída': 'Sortie',
    'Nome do Empregado': 'Nom de l\'Employé',
    'Código do Produto': 'Code Produit',
    'Nome do Material': 'Nom du Matériel',
    'Quantidade': 'Quantité',
    'Unidade de Medida': 'Unité de Mesure',
    'Stock Mínimo (Alerta)': 'Stock Minimum (Alerte)',
    'Obra / Destino': 'Chantier / Destination',
    'Selecione a Obra': 'Sélectionnez le Chantier',
    'Histórico de Movimentos': 'Historique des Mouvements',
    'Data/Hora': 'Date/Heure',
    'Obra': 'Chantier',
    'Registar Sobra (Entrada no Banco)': 'Enregistrer Excédent',
    'Material Disponível': 'Matériel Disponible',
    'Localização Atual / Obra': 'Localisation Actuelle / Chantier',
    'Disponibilizar Sobra para a Equipa': 'Mettre à Disposition',
    'Materiais Excédentaires': 'Matériaux Excédentaires',
    'Data': 'Date',
    'Dar Baixa': 'Retirer',
    'Utilizado': 'Utilisé',
    'Nenhuma sobra registada.': 'Aucun excédent enregistré.',
    'Gestão de Obras': 'Gestion des Chantiers',
    'Nova Obra': 'Nouveau Chantier',
    'Nome da Obra': 'Nom du Chantier',
    'Morada / Localização': 'Adresse / Localisation',
    'Registar Obra': 'Enregistrer Chantier',
    'Obras Registadas': 'Chantiers Enregistrés',
    'Sem obras registadas.': 'Aucun chantier enregistré.',
    'Armazém Central': 'Dépôt Central',
    'Gestão de Funcionários': 'Gestion des Employés',
    'Novo Funcionário': 'Nouvel Employé',
    'Utilizador (Login)': 'Utilisateur (Login)',
    'Senha': 'Mot de passe',
    'Nome Completo': 'Nom Complet',
    'Perfil': 'Profil',
    'Registar Funcionário': 'Enregistrer Employé',
    'Funcionários Registados': 'Employés Enregistrés',
    'Administrador': 'Administrateur',
    'Ativo': 'Actif',
    'Bloqueado': 'Bloqué',
    'Bloquear': 'Bloquer',
    'Desbloquear': 'Débloquear',
    'Nova Senha': 'Nouveau Mot de passe',
    'Alterar Senha': 'Changer Mot de passe',
    'Editar': 'Modifier',
    'Salvar Alterações': 'Enregistrer les Modifications',
    'Cancelar': 'Annuler'
}

@app.context_processor
def inject_translator():
    lang = session.get('lang', 'pt')
    def t(word):
        if lang == 'fr':
            return FR_DICT.get(word, word)
        return word
    return dict(t=t, lang=lang)

def get_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('''CREATE TABLE IF NOT EXISTS obras (id SERIAL PRIMARY KEY, nome TEXT NOT NULL, localizacao TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS movimentos (id SERIAL PRIMARY KEY, data_hora TEXT NOT NULL, tipo_movimento TEXT NOT NULL, nome_empregado TEXT NOT NULL, codigo_produto TEXT DEFAULT '', nome_material TEXT NOT NULL, quantidade REAL NOT NULL, unidade TEXT NOT NULL DEFAULT 'unidades', stock_minimo REAL DEFAULT 5, obra TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS sobras (id SERIAL PRIMARY KEY, data_hora TEXT NOT NULL, nome_empregado TEXT NOT NULL, material TEXT NOT NULL, quantidade REAL NOT NULL, unidade TEXT NOT NULL DEFAULT 'unidades', localizacao_atual TEXT NOT NULL, estado TEXT NOT NULL)''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utilizadores (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome TEXT NOT NULL,
                perfil TEXT NOT NULL,
                estado TEXT DEFAULT 'Ativo'
            )
        ''')
    else:
        cursor.execute('''CREATE TABLE IF NOT EXISTS obras (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, localizacao TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS movimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT NOT NULL, tipo_movimento TEXT NOT NULL, nome_empregado TEXT NOT NULL, codigo_produto TEXT DEFAULT '', nome_material TEXT NOT NULL, quantidade REAL NOT NULL, unidade TEXT NOT NULL DEFAULT 'unidades', stock_minimo REAL DEFAULT 5, obra TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS sobras (id INTEGER PRIMARY KEY AUTOINCREMENT, data_hora TEXT NOT NULL, nome_empregado TEXT NOT NULL, material TEXT NOT NULL, quantidade REAL NOT NULL, unidade TEXT NOT NULL DEFAULT 'unidades', localizacao_atual TEXT NOT NULL, estado TEXT NOT NULL)''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utilizadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome TEXT NOT NULL,
                perfil TEXT NOT NULL,
                estado TEXT DEFAULT 'Ativo'
            )
        ''')
    
    cursor.execute("SELECT COUNT(*) as count FROM obras")
    res = cursor.fetchone()
    count_obras = res['count'] if DATABASE_URL else res[0]
    if count_obras == 0:
        cursor.execute("INSERT INTO obras (nome, localizacao) VALUES (%s, %s)" if DATABASE_URL else "INSERT INTO obras (nome, localizacao) VALUES (?, ?)", ('Armazém Central', 'Sede'))
        
    cursor.execute("SELECT COUNT(*) as count FROM utilizadores")
    res_u = cursor.fetchone()
    count_users = res_u['count'] if DATABASE_URL else res_u[0]
    if count_users == 0:
        default_users = [
            ('admin', 'admin123', 'Administrador', 'admin', 'Ativo'),
            ('gustavo', 'obra123', 'Gustavo', 'funcionario', 'Ativo'),
            ('diogo', 'obra123', 'Diogo', 'funcionario', 'Ativo'),
            ('lara', 'obra123', 'Lara', 'funcionario', 'Ativo')
        ]
        if DATABASE_URL:
            for u in default_users:
                cursor.execute("INSERT INTO utilizadores (username, senha, nome, perfil, estado) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (username) DO NOTHING", u)
        else:
            cursor.executemany("INSERT OR IGNORE INTO utilizadores (username, senha, nome, perfil, estado) VALUES (?, ?, ?, ?, ?)", default_users)
        
    conn.commit()
    conn.close()

@app.route('/lang/<idioma>')
def set_lang(idioma):
    session['lang'] = idioma
    return redirect(request.referrer or url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        senha = request.form.get('senha', '')
        db = get_db()
        cursor = db.cursor()
        if DATABASE_URL:
            cursor.execute("SELECT * FROM utilizadores WHERE username = %s AND senha = %s", (username, senha))
        else:
            cursor.execute("SELECT * FROM utilizadores WHERE username = ? AND senha = ?", (username, senha))
        user = cursor.fetchone()
        db.close()
        if user:
            if user['estado'] == 'Bloqueado':
                flash('Este utilizador encontra-se bloqueado.', 'error')
            else:
                session['user'] = user['username']
                session['perfil'] = user['perfil']
                session['nome'] = user['nome']
                return redirect(url_for('index'))
        else:
            flash('Erro de login', 'error')
    return render_template_string(HTML_LOGIN)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT COUNT(DISTINCT nome_material) as count FROM movimentos")
    total_materiais = cursor.fetchone()['count'] or 0
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    if DATABASE_URL:
        cursor.execute("SELECT COUNT(*) as count FROM movimentos WHERE tipo_movimento = 'Entrada' AND data_hora LIKE %s", (f"{today_str}%",))
    else:
        cursor.execute("SELECT COUNT(*) as count FROM movimentos WHERE tipo_movimento = 'Entrada' AND data_hora LIKE ?", (f"{today_str}%",))
    entradas_hoje = cursor.fetchone()['count']
    
    if DATABASE_URL:
        cursor.execute("SELECT COUNT(*) as count FROM movimentos WHERE tipo_movimento = 'Saída' AND data_hora LIKE %s", (f"{today_str}%",))
    else:
        cursor.execute("SELECT COUNT(*) as count FROM movimentos WHERE tipo_movimento = 'Saída' AND data_hora LIKE ?", (f"{today_str}%",))
    saidas_hoje = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM sobras WHERE estado = 'Disponível'")
    sobras_disp = cursor.fetchone()['count'] or 0
    
    cursor.execute("SELECT * FROM movimentos ORDER BY id DESC LIMIT 5")
    ultimos_movimentos = cursor.fetchall()
    
    # Sobras recentes agrupadas/somadas para o dashboard
    cursor.execute("""
        SELECT MIN(id) as id, MAX(data_hora) as data_hora, material, SUM(quantidade) as quantidade, unidade, localizacao_atual, 'Disponível' as estado 
        FROM sobras WHERE estado = 'Disponível' 
        GROUP BY material, unidade, localizacao_atual 
        ORDER BY id DESC LIMIT 5
    """)
    sobras_recentes = cursor.fetchall()
    db.close()
    
    return render_template_string(HTML_LAYOUT.replace('<!--CONTENT-->', HTML_DASHBOARD), active='dashboard', 
                                  total_materiais=total_materiais, entradas_hoje=entradas_hoje, saidas_hoje=saidas_hoje, 
                                  sobras_disp=sobras_disp, ultimos_movimentos=ultimos_movimentos, sobras_recentes=sobras_recentes)

@app.route('/estoque')
def estoque():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    query = """
        SELECT codigo_produto, nome_material, unidade,
               COALESCE(MAX(stock_minimo), 5) as stock_minimo,
               COALESCE(SUM(CASE WHEN tipo_movimento = 'Entrada' THEN quantidade ELSE -quantidade END), 0) as saldo_atual
        FROM movimentos GROUP BY codigo_produto, nome_material, unidade HAVING SUM(CASE WHEN tipo_movimento = 'Entrada' THEN quantidade ELSE -quantidade END) > 0
    """
    cursor.execute(query)
    itens_estoque = cursor.fetchall()
    db.close()
    return render_template_string(HTML_LAYOUT.replace('<!--CONTENT-->', HTML_ESTOQUE), active='estoque', itens_estoque=itens_estoque)

@app.route('/obras', methods=['GET', 'POST'])
def obras():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        nome = request.form.get('nome')
        local = request.form.get('localizacao')
        if DATABASE_URL:
            cursor.execute("INSERT INTO obras (nome, localizacao) VALUES (%s, %s)", (nome, local))
        else:
            cursor.execute("INSERT INTO obras (nome, localizacao) VALUES (?, ?)", (nome, local))
        db.commit()
        db.close()
        return redirect(url_for('obras'))
    cursor.execute("SELECT * FROM obras ORDER BY id DESC")
    todas_obras = cursor.fetchall()
    db.close()
    return render_template_string(HTML_LAYOUT.replace('<!--CONTENT-->', HTML_OBRAS), active='obras', obras=todas_obras)

@app.route('/obras/editar/<int:id>', methods=['POST'])
def editar_obra(id):
    if 'user' not in session: return redirect(url_for('login'))
    novo_nome = request.form.get('nome')
    nova_localizacao = request.form.get('localizacao')
    db = get_db()
    cursor = db.cursor()
    if DATABASE_URL:
        cursor.execute("UPDATE obras SET nome = %s, localizacao = %s WHERE id = %s", (novo_nome, nova_localizacao, id))
    else:
        cursor.execute("UPDATE obras SET nome = ?, localizacao = ? WHERE id = ?", (novo_nome, nova_localizacao, id))
    db.commit()
    db.close()
    return redirect(url_for('obras'))

@app.route('/funcionarios', methods=['GET', 'POST'])
def funcionarios():
    if 'user' not in session or session['perfil'] != 'admin': 
        return redirect(url_for('index'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        username = request.form.get('username').strip().lower()
        senha = request.form.get('senha')
        nome = request.form.get('nome')
        perfil = request.form.get('perfil')
        try:
            if DATABASE_URL:
                cursor.execute("INSERT INTO utilizadores (username, senha, nome, perfil, estado) VALUES (%s, %s, %s, %s, 'Ativo')", (username, senha, nome, perfil))
            else:
                cursor.execute("INSERT INTO utilizadores (username, senha, nome, perfil, estado) VALUES (?, ?, ?, ?, 'Ativo')", (username, senha, nome, perfil))
            db.commit()
        except Exception:
            pass
        db.close()
        return redirect(url_for('funcionarios'))
    cursor.execute("SELECT * FROM utilizadores ORDER BY id DESC")
    todos_funcs = cursor.fetchall()
    db.close()
    return render_template_string(HTML_LAYOUT.replace('<!--CONTENT-->', HTML_FUNCIONARIOS), active='funcionarios', funcionarios=todos_funcs)

@app.route('/funcionarios/editar/<int:id>', methods=['POST'])
def editar_funcionario(id):
    if 'user' not in session or session['perfil'] != 'admin': return redirect(url_for('index'))
    novo_user = request.form.get('username').strip().lower()
    novo_nome = request.form.get('nome')
    novo_perfil = request.form.get('perfil')
    db = get_db()
    cursor = db.cursor()
    if DATABASE_URL:
        cursor.execute("UPDATE utilizadores SET username = %s, nome = %s, perfil = %s WHERE id = %s", (novo_user, novo_nome, novo_perfil, id))
    else:
        cursor.execute("UPDATE utilizadores SET username = ?, nome = ?, perfil = ? WHERE id = ?", (novo_user, novo_nome, novo_perfil, id))
    db.commit()
    db.close()
    return redirect(url_for('funcionarios'))

@app.route('/funcionarios/status/<int:id>', methods=['POST'])
def alterar_status_funcionario(id):
    if 'user' not in session or session['perfil'] != 'admin': return redirect(url_for('index'))
    db = get_db()
    cursor = db.cursor()
    if DATABASE_URL:
        cursor.execute("SELECT * FROM utilizadores WHERE id = %s", (id,))
    else:
        cursor.execute("SELECT * FROM utilizadores WHERE id = ?", (id,))
    user = cursor.fetchone()
    if user and user['username'] != 'admin':
        novo_estado = 'Bloqueado' if user['estado'] == 'Ativo' else 'Ativo'
        if DATABASE_URL:
            cursor.execute("UPDATE utilizadores SET estado = %s WHERE id = %s", (novo_estado, id))
        else:
            cursor.execute("UPDATE utilizadores SET estado = ? WHERE id = ?", (novo_estado, id))
        db.commit()
    db.close()
    return redirect(url_for('funcionarios'))

@app.route('/funcionarios/senha/<int:id>', methods=['POST'])
def alterar_senha_funcionario(id):
    if 'user' not in session or session['perfil'] != 'admin': return redirect(url_for('index'))
    nova_senha = request.form.get('nova_senha')
    if nova_senha:
        db = get_db()
        cursor = db.cursor()
        if DATABASE_URL:
            cursor.execute("UPDATE utilizadores SET senha = %s WHERE id = %s", (nova_senha, id))
        else:
            cursor.execute("UPDATE utilizadores SET senha = ? WHERE id = ?", (nova_senha, id))
        db.commit()
        db.close()
    return redirect(url_for('funcionarios'))

@app.route('/movimentos', methods=['GET', 'POST'])
def movimentos():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        tipo = 'Saída' if session['perfil'] == 'funcionario' else request.form.get('tipo_movimento')
        empregado = session['nome'] if session['perfil'] == 'funcionario' else (request.form.get('nome_empregado') or session['nome'])
        codigo = request.form.get('codigo_produto', '')
        material = request.form.get('nome_material')
        qtd = float(request.form.get('quantidade'))
        unidade = request.form.get('unidade', 'unidades')
        stock_minimo = float(request.form.get('stock_minimo', 5))
        obra = request.form.get('obra')
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if DATABASE_URL:
            cursor.execute("INSERT INTO movimentos (data_hora, tipo_movimento, nome_empregado, codigo_produto, nome_material, quantidade, unidade, stock_minimo, obra) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                           (data_hora, tipo, empregado, codigo, material, qtd, unidade, stock_minimo, obra))
        else:
            cursor.execute("INSERT INTO movimentos (data_hora, tipo_movimento, nome_empregado, codigo_produto, nome_material, quantidade, unidade, stock_minimo, obra) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (data_hora, tipo, empregado, codigo, material, qtd, unidade, stock_minimo, obra))
        db.commit()
        db.close()
        return redirect(url_for('movimentos'))
        
    cursor.execute("SELECT * FROM movimentos ORDER BY id DESC")
    todos_movimentos = cursor.fetchall()
    cursor.execute("SELECT * FROM obras ORDER BY nome")
    todas_obras = cursor.fetchall()
    db.close()
    return render_template_string(HTML_LAYOUT.replace('<!--CONTENT-->', HTML_MOVIMENTOS), active='movimentos', movimentos=todos_movimentos, obras=todas_obras)

@app.route('/exportar')
def exportar():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM movimentos ORDER BY id DESC")
    movimentos = cursor.fetchall()
    db.close()
    si = StringIO()
    cw = csv.writer(si, delimiter=';')
    cw.writerow(['ID', 'Data', 'Tipo', 'Empregado', 'Codigo Produto', 'Material', 'Quantidade', 'Unidade', 'Obra'])
    for m in movimentos:
        cw.writerow([m['id'], m['data_hora'], m['tipo_movimento'], m['nome_empregado'], m['codigo_produto'], m['nome_material'], m['quantidade'], m['unidade'], m['obra']])
    output = '\ufeff' + si.getvalue()
    return Response(output, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=relatorio_movimentos.csv"})

@app.route('/sobras', methods=['GET', 'POST'])
def sobras():
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        empregado = session['nome']
        material = request.form.get('material').strip()
        qtd = float(request.form.get('quantidade'))
        unidade = request.form.get('unidade', 'unidades')
        local = request.form.get('localizacao_atual')
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if DATABASE_URL:
            cursor.execute("INSERT INTO sobras (data_hora, nome_empregado, material, quantidade, unidade, localizacao_atual, estado) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                           (data_hora, empregado, material, qtd, unidade, local, 'Disponível'))
        else:
            cursor.execute("INSERT INTO sobras (data_hora, nome_empregado, material, quantidade, unidade, localizacao_atual, estado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (data_hora, empregado, material, qtd, unidade, local, 'Disponível'))
        db.commit()
        db.close()
        return redirect(url_for('sobras'))
        
    # Consulta agrupada para somar as sobras disponíveis do mesmo material, unidade e local
    cursor.execute("""
        SELECT MIN(id) as id, MAX(data_hora) as data_hora, material, SUM(quantidade) as quantidade, unidade, localizacao_atual, 'Disponível' as estado 
        FROM sobras WHERE estado = 'Disponível' 
        GROUP BY material, unidade, localizacao_atual 
        ORDER BY id DESC
    """)
    todas_sobras = cursor.fetchall()
    
    cursor.execute("SELECT * FROM obras ORDER BY nome")
    todas_obras = cursor.fetchall()
    db.close()
    return render_template_string(HTML_LAYOUT.replace('<!--CONTENT-->', HTML_SOBRAS), active='sobras', sobras=todas_sobras, obras=todas_obras)

@app.route('/sobras/usar/<int:id>', methods=['POST'])
def usar_sobra(id):
    if 'user' not in session: return redirect(url_for('login'))
    db = get_db()
    cursor = db.cursor()
    
    # Como o ID devolvido é o MIN(id) do grupo, vamos buscar o material, unidade e local correspondentes
    if DATABASE_URL:
        cursor.execute("SELECT * FROM sobras WHERE id = %s", (id,))
    else:
        cursor.execute("SELECT * FROM sobras WHERE id = ?", (id,))
    sobra_ref = cursor.fetchone()
    
    if sobra_ref:
        material = sobra_ref['material']
        unidade = sobra_ref['unidade']
        local = sobra_ref['localizacao_atual']
        qtd_retirar = float(request.form.get('quantidade_retirar', 0))
        obra_destino = request.form.get('obra_destino', 'Obra Geral')
        data_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Obter todas as linhas ativas deste material/local para dar baixa por ordem de registo (FIFO)
        if DATABASE_URL:
            cursor.execute("SELECT * FROM sobras WHERE material = %s AND unidade = %s AND localizacao_atual = %s AND estado = 'Disponível' ORDER BY id ASC", (material, unidade, local))
        else:
            cursor.execute("SELECT * FROM sobras WHERE material = ? AND unidade = ? AND localizacao_atual = ? AND estado = 'Disponível' ORDER BY id ASC", (material, unidade, local))
        registros = cursor.fetchall()
        
        restante = qtd_retirar
        for reg in registros:
            if restante <= 0:
                break
            reg_id = reg['id']
            reg_qtd = reg['quantidade']
            if restante >= reg_qtd:
                if DATABASE_URL:
                    cursor.execute("UPDATE sobras SET estado = 'Utilizado' WHERE id = %s", (reg_id,))
                else:
                    cursor.execute("UPDATE sobras SET estado = 'Utilizado' WHERE id = ?", (reg_id,))
                restante -= reg_qtd
            else:
                nova_qtd = reg_qtd - restante
                if DATABASE_URL:
                    cursor.execute("UPDATE sobras SET quantidade = %s WHERE id = %s", (nova_qtd, reg_id))
                else:
                    cursor.execute("UPDATE sobras SET quantidade = ? WHERE id = ?", (nova_qtd, reg_id))
                restante = 0
                
        if qtd_retirar > 0:
            if DATABASE_URL:
                cursor.execute("INSERT INTO movimentos (data_hora, tipo_movimento, nome_empregado, codigo_produto, nome_material, quantidade, unidade, stock_minimo, obra) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                               (data_hora, 'Saída', session['nome'], 'SOBRA', material, qtd_retirar, unidade, 0, obra_destino))
            else:
                cursor.execute("INSERT INTO movimentos (data_hora, tipo_movimento, nome_empregado, codigo_produto, nome_material, quantidade, unidade, stock_minimo, obra) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (data_hora, 'Saída', session['nome'], 'SOBRA', material, qtd_retirar, unidade, 0, obra_destino))
        db.commit()
    db.close()
    return redirect(url_for('sobras'))


# TEMPLATES HTML
HTML_LOGIN = '''
<!DOCTYPE html>
<html lang="pt">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-900 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-3xl shadow-2xl w-full max-w-md">
        <h1 class="text-2xl font-extrabold text-slate-900 text-center mb-6">CLIMA POSITIVO</h1>
        <form method="POST" class="space-y-4">
            <div><label class="block text-xs font-semibold uppercase text-slate-500 mb-1">Utilizador</label><input type="text" name="username" required class="w-full rounded-xl border px-4 py-3"></div>
            <div><label class="block text-xs font-semibold uppercase text-slate-500 mb-1">Senha</label><input type="password" name="senha" required class="w-full rounded-xl border px-4 py-3"></div>
            <button type="submit" class="w-full bg-orange-600 text-white py-3 rounded-xl font-bold">Login</button>
        </form>
    </div>
</body>
</html>
'''

HTML_LAYOUT = '''
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CLIMA POSITIVO</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body class="bg-gray-50 font-sans antialiased pb-20 md:pb-0">
    <div class="flex h-screen overflow-hidden">
        <aside class="hidden md:flex flex-col w-64 bg-slate-900 border-r border-slate-800 text-white">
            <div class="p-6 flex items-center space-x-3 border-b border-slate-800">
                <div class="bg-orange-500 p-2 rounded-lg font-bold"><i class="fa-solid fa-boxes-stacked"></i></div>
                <div><h1 class="font-bold text-lg">CLIMA POSITIVO</h1><p class="text-xs text-slate-400">{{ t('Controlo de Obra & Stock') }}</p></div>
            </div>
            <nav class="flex-1 px-4 py-6 space-y-2">
                <a href="/" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition {{ 'bg-orange-500 shadow-lg font-bold' if active == 'dashboard' else 'text-slate-300 hover:bg-slate-800' }}"><i class="fa-solid fa-chart-pie w-5"></i><span>{{ t('Resumo') }}</span></a>
                <a href="/obras" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition {{ 'bg-orange-500 shadow-lg font-bold' if active == 'obras' else 'text-slate-300 hover:bg-slate-800' }}"><i class="fa-solid fa-helmet-safety w-5"></i><span>{{ t('Obras') }}</span></a>
                <a href="/estoque" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition {{ 'bg-orange-500 shadow-lg font-bold' if active == 'estoque' else 'text-slate-300 hover:bg-slate-800' }}"><i class="fa-solid fa-box w-5"></i><span>{{ t('Estoque') }}</span></a>
                <a href="/movimentos" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition {{ 'bg-orange-500 shadow-lg font-bold' if active == 'movimentos' else 'text-slate-300 hover:bg-slate-800' }}"><i class="fa-solid fa-right-left w-5"></i><span>{{ t('Movimentos') }}</span></a>
                <a href="/sobras" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition {{ 'bg-orange-500 shadow-lg font-bold' if active == 'sobras' else 'text-slate-300 hover:bg-slate-800' }}"><i class="fa-solid fa-recycle w-5"></i><span>{{ t('Banco de Sobras') }}</span></a>
                {% if session['perfil'] == 'admin' %}
                <a href="/funcionarios" class="flex items-center space-x-3 px-4 py-3 rounded-xl transition {{ 'bg-orange-500 shadow-lg font-bold' if active == 'funcionarios' else 'text-slate-300 hover:bg-slate-800' }}"><i class="fa-solid fa-users w-5"></i><span>{{ t('Funcionários') }}</span></a>
                {% endif %}
            </nav>
            <div class="p-4 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
                <div><p class="font-bold text-white">{{ session['nome'] }}</p><p class="text-[10px] text-orange-400 uppercase">{{ session['perfil'] }}</p></div>
                <a href="/logout" class="bg-slate-800 hover:bg-red-600 text-white p-2 rounded-xl transition"><i class="fa-solid fa-power-off"></i></a>
            </div>
        </aside>
        <div class="flex-1 flex flex-col overflow-y-auto">
            <header class="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center shadow-sm sticky top-0 z-10">
                <div class="flex items-center space-x-4"><span class="text-xl font-bold text-slate-800 md:hidden">CLIMA POSITIVO</span><span class="text-sm font-semibold text-gray-500 hidden md:inline">{{ t('Gestão de Materiais e Excedentes') }}</span></div>
                <div class="flex items-center space-x-4">
                    <div class="flex items-center bg-gray-100 rounded-lg p-1 mr-2">
                        <a href="/lang/pt" class="px-2 py-1 text-xs rounded-md {{ 'bg-white shadow font-bold text-slate-800' if lang == 'pt' else 'text-gray-500' }}">PT</a>
                        <a href="/lang/fr" class="px-2 py-1 text-xs rounded-md {{ 'bg-white shadow font-bold text-slate-800' if lang == 'fr' else 'text-gray-500' }}">FR</a>
                    </div>
                    <a href="/movimentos" class="bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-xl text-sm font-medium shadow-md transition flex items-center space-x-2">
                        <i class="fa-solid fa-plus"></i><span>{{ t('Registar Saída') if session['perfil'] == 'funcionario' else t('Registar Movimento') }}</span>
                    </a>
                </div>
            </header>
            <main class="p-4 md:p-8 flex-1"><!--CONTENT--></main>
        </div>
    </div>
</body>
</html>
'''

HTML_DASHBOARD = '''
<div class="mb-8">
    <h2 class="text-2xl font-bold text-slate-900">{{ t('Resumo') }}</h2>
    <p class="text-sm text-gray-500">{{ t('Gestão de Materiais e Excedentes') }}</p>
</div>

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <div class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between"><div><p class="text-xs font-semibold uppercase text-gray-400 mb-1">{{ t('Materiais') }}</p><h3 class="text-3xl font-extrabold text-slate-900">{{ total_materiais }}</h3></div><div class="w-12 h-12 bg-orange-50 text-orange-600 rounded-xl flex items-center justify-center text-xl font-bold"><i class="fa-solid fa-box"></i></div></div>
    <div class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between"><div><p class="text-xs font-semibold uppercase text-gray-400 mb-1">{{ t('Entradas Hoje') }}</p><h3 class="text-3xl font-extrabold text-slate-900">{{ entradas_hoje }}</h3></div><div class="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center text-xl font-bold"><i class="fa-solid fa-arrow-down"></i></div></div>
    <div class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between"><div><p class="text-xs font-semibold uppercase text-gray-400 mb-1">{{ t('Saídas Hoje') }}</p><h3 class="text-3xl font-extrabold text-slate-900">{{ saidas_hoje }}</h3></div><div class="w-12 h-12 bg-rose-50 text-rose-600 rounded-xl flex items-center justify-center text-xl font-bold"><i class="fa-solid fa-arrow-up"></i></div></div>
    <div class="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between"><div><p class="text-xs font-semibold uppercase text-gray-400 mb-1">{{ t('Sobras Disp.') }}</p><h3 class="text-3xl font-extrabold text-slate-900">{{ sobras_disp }}</h3></div><div class="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center text-xl font-bold"><i class="fa-solid fa-recycle"></i></div></div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div class="flex justify-between items-center mb-6"><h3 class="font-bold text-lg text-slate-900">{{ t('Últimos Movimentos') }}</h3><a href="/movimentos" class="text-sm font-semibold text-orange-600">{{ t('Ver Todos') }}</a></div>
        <div class="overflow-x-auto"><table class="w-full text-left border-collapse">
            <thead><tr class="border-b border-gray-100 text-xs font-semibold text-gray-400 uppercase"><th class="pb-3">{{ t('Tipo') }}</th><th class="pb-3">{{ t('Material') }}</th><th class="pb-3">{{ t('Qtd') }}</th><th class="pb-3">{{ t('Funcionário') }}</th></tr></thead>
            <tbody class="divide-y divide-gray-50 text-sm">
                {% for m in ultimos_movimentos %}
                <tr class="hover:bg-gray-50/50">
                    <td class="py-3"><span class="px-2.5 py-1 rounded-full text-xs font-semibold {{ 'bg-green-100 text-green-700' if m.tipo_movimento == 'Entrada' else 'bg-red-100 text-red-700' }}">{{ t(m.tipo_movimento) }}</span></td>
                    <td class="py-3 font-medium text-slate-800">{{ m.nome_material }}</td>
                    <td class="py-3 text-gray-600">{{ m.quantidade }} {{ m.unidade }}</td>
                    <td class="py-3 text-gray-500">{{ m.nome_empregado }}</td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="py-6 text-center text-gray-400 text-sm">{{ t('Nenhum movimento registado.') }}</td></tr>
                {% endfor %}
            </tbody>
        </table></div>
    </div>

    <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div class="flex justify-between items-center mb-6"><h3 class="font-bold text-lg text-slate-900">{{ t('Banco de Sobras Ativas') }}</h3><a href="/sobras" class="text-sm font-semibold text-orange-600">{{ t('Gerir Sobras') }}</a></div>
        <div class="overflow-x-auto"><table class="w-full text-left border-collapse">
            <thead><tr class="border-b border-gray-100 text-xs font-semibold text-gray-400 uppercase"><th class="pb-3">{{ t('Material') }}</th><th class="pb-3">{{ t('Qtd') }}</th><th class="pb-3">{{ t('Local') }}</th><th class="pb-3">{{ t('Ação') }}</th></tr></thead>
            <tbody class="divide-y divide-gray-50 text-sm">
                {% for s in sobras_recentes %}
                <tr class="hover:bg-gray-50/50">
                    <td class="py-3 font-medium text-slate-800">{{ s.material }}</td>
                    <td class="py-3 text-gray-600">{{ s.quantidade }} {{ s.unidade }}</td>
                    <td class="py-3 text-gray-500">{{ s.localizacao_atual }}</td>
                    <td class="py-3"><a href="/sobras" class="bg-slate-100 hover:bg-emerald-600 hover:text-white text-slate-700 px-3 py-1 rounded-lg text-xs font-semibold transition">{{ t('Utilizar') }}</a></td>
                </tr>
                {% else %}
                <tr><td colspan="4" class="py-6 text-center text-gray-400 text-sm">{{ t('Nenhuma sobra disponível.') }}</td></tr>
                {% endfor %}
            </tbody>
        </table></div>
    </div>
</div>
'''

HTML_OBRAS = '''
<div class="bg-white rounded-2xl border shadow-sm p-6 mb-8">
    <h2 class="font-bold text-lg text-slate-900 mb-4">{{ t('Nova Obra') }}</h2>
    <form method="POST" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Nome da Obra') }}</label><input type="text" name="nome" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Morada / Localização') }}</label><input type="text" name="localizacao" class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div class="md:col-span-2"><button type="submit" class="bg-slate-800 text-white py-2.5 px-6 rounded-xl font-medium">{{ t('Registar Obra') }}</button></div>
    </form>
</div>
<div class="bg-white rounded-2xl border shadow-sm p-6">
    <h3 class="font-bold text-lg text-slate-900 mb-4">{{ t('Obras Registadas') }}</h3>
    <div class="overflow-x-auto"><table class="w-full text-left">
        <thead><tr class="border-b text-xs text-gray-400 uppercase"><th class="pb-3">ID</th><th class="pb-3">{{ t('Nome da Obra') }}</th><th class="pb-3">{{ t('Morada / Localização') }}</th><th class="pb-3" style="min-width: 250px;">{{ t('Ação') }}</th></tr></thead>
        <tbody class="divide-y text-sm">
            {% for o in obras %}
            <tr class="hover:bg-gray-50">
                <td class="py-3 text-gray-400">#{{ o.id }}</td>
                <td class="py-3 font-bold text-slate-800">{{ o.nome }}</td>
                <td class="py-3 text-gray-500">{{ o.localizacao }}</td>
                <td class="py-3">
                    <button onclick="document.getElementById('edit-obra-{{ o.id }}').classList.toggle('hidden')" class="bg-blue-50 text-blue-600 border border-blue-200 hover:bg-blue-600 hover:text-white px-3 py-1 rounded-lg text-xs font-semibold">
                        {{ t('Editar') }}
                    </button>
                </td>
            </tr>
            <tr id="edit-obra-{{ o.id }}" class="hidden bg-slate-50">
                <td colspan="4" class="p-4">
                    <form action="/obras/editar/{{ o.id }}" method="POST" class="flex flex-wrap items-center gap-3">
                        <div class="text-xs font-bold text-slate-700">{{ t('Editar') }}:</div>
                        <input type="text" name="nome" value="{{ o.nome }}" required class="rounded-lg border px-2 py-1 text-xs" placeholder="Nome da Obra">
                        <input type="text" name="localizacao" value="{{ o.localizacao }}" class="rounded-lg border px-2 py-1 text-xs" placeholder="Localização">
                        <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded-lg text-xs font-bold">{{ t('Salvar Alterações') }}</button>
                        <button type="button" onclick="document.getElementById('edit-obra-{{ o.id }}').classList.add('hidden')" class="bg-gray-200 text-gray-700 px-3 py-1 rounded-lg text-xs">{{ t('Cancelar') }}</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="4" class="py-6 text-center text-gray-400">{{ t('Sem obras registadas.') }}</td></tr>
            {% endfor %}
        </tbody>
    </table></div>
</div>
'''

HTML_FUNCIONARIOS = '''
<div class="bg-white rounded-2xl border shadow-sm p-6 mb-8">
    <h2 class="font-bold text-lg text-slate-900 mb-4">{{ t('Novo Funcionário') }}</h2>
    <form method="POST" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Utilizador (Login)') }}</label><input type="text" name="username" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Senha') }}</label><input type="password" name="senha" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Nome Completo') }}</label><input type="text" name="nome" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Perfil') }}</label>
            <select name="perfil" class="w-full rounded-xl border px-4 py-2.5 text-sm">
                <option value="funcionario">{{ t('Funcionário') }}</option>
                <option value="admin">{{ t('Administrador') }}</option>
            </select>
        </div>
        <div class="lg:col-span-4 mt-2"><button type="submit" class="w-full bg-slate-800 text-white py-3 rounded-xl font-medium">{{ t('Registar Funcionário') }}</button></div>
    </form>
</div>
<div class="bg-white rounded-2xl border shadow-sm p-6">
    <h3 class="font-bold text-lg text-slate-900 mb-4">{{ t('Funcionários Registados') }}</h3>
    <div class="overflow-x-auto"><table class="w-full text-left">
        <thead><tr class="border-b text-xs text-gray-400 uppercase"><th class="pb-3">ID</th><th class="pb-3">{{ t('Utilizador (Login)') }}</th><th class="pb-3">{{ t('Nome Completo') }}</th><th class="pb-3">{{ t('Perfil') }}</th><th class="pb-3">{{ t('Estado') }}</th><th class="pb-3" style="min-width: 450px;">{{ t('Ação') }}</th></tr></thead>
        <tbody class="divide-y text-sm">
            {% for f in funcionarios %}
            <tr class="hover:bg-gray-50">
                <td class="py-3 text-gray-400">#{{ f.id }}</td>
                <td class="py-3 font-mono text-xs font-bold">{{ f.username }}</td>
                <td class="py-3 font-medium">{{ f.nome }}</td>
                <td class="py-3"><span class="px-2.5 py-1 rounded-full text-xs font-semibold {{ 'bg-purple-100 text-purple-700' if f.perfil == 'admin' else 'bg-blue-100 text-blue-700' }}">{{ t(f.perfil.capitalize()) }}</span></td>
                <td class="py-3"><span class="px-2.5 py-1 rounded-full text-xs font-semibold {{ 'bg-emerald-100 text-emerald-700' if f.estado == 'Ativo' else 'bg-red-100 text-red-700' }}">{{ t(f.estado) }}</span></td>
                <td class="py-3 flex flex-wrap items-center gap-2">
                    {% if f.username != 'admin' %}
                    <form action="/funcionarios/status/{{ f.id }}" method="POST">
                        <button type="submit" class="px-3 py-1 rounded-lg text-xs font-semibold border {{ 'bg-red-50 text-red-600 border-red-200 hover:bg-red-600 hover:text-white' if f.estado == 'Ativo' else 'bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-600 hover:text-white' }}">
                            {{ t('Bloquear') if f.estado == 'Ativo' else t('Desbloquear') }}
                        </button>
                    </form>
                    {% endif %}
                    <button onclick="document.getElementById('edit-{{ f.id }}').classList.toggle('hidden')" class="bg-blue-50 text-blue-600 border border-blue-200 hover:bg-blue-600 hover:text-white px-3 py-1 rounded-lg text-xs font-semibold">
                        {{ t('Editar') }}
                    </button>
                    <form action="/funcionarios/senha/{{ f.id }}" method="POST" class="flex items-center space-x-1">
                        <input type="password" name="nova_senha" placeholder="{{ t('Nova Senha') }}" required class="w-20 rounded-lg border px-2 py-1 text-xs">
                        <button type="submit" class="bg-slate-100 hover:bg-slate-800 hover:text-white text-slate-700 px-2 py-1 rounded-lg text-xs font-semibold border">{{ t('Alterar Senha') }}</button>
                    </form>
                </td>
            </tr>
            <tr id="edit-{{ f.id }}" class="hidden bg-slate-50">
                <td colspan="6" class="p-4">
                    <form action="/funcionarios/editar/{{ f.id }}" method="POST" class="flex flex-wrap items-center gap-3">
                        <div class="text-xs font-bold text-slate-700">{{ t('Editar') }}:</div>
                        <input type="text" name="username" value="{{ f.username }}" required class="rounded-lg border px-2 py-1 text-xs" placeholder="Login">
                        <input type="text" name="nome" value="{{ f.nome }}" required class="rounded-lg border px-2 py-1 text-xs" placeholder="Nome">
                        <select name="perfil" class="rounded-lg border px-2 py-1 text-xs">
                            <option value="funcionario" {{ 'selected' if f.perfil == 'funcionario' else '' }}>{{ t('Funcionário') }}</option>
                            <option value="admin" {{ 'selected' if f.perfil == 'admin' else '' }}>{{ t('Administrador') }}</option>
                        </select>
                        <button type="submit" class="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 rounded-lg text-xs font-bold">{{ t('Salvar Alterações') }}</button>
                        <button type="button" onclick="document.getElementById('edit-{{ f.id }}').classList.add('hidden')" class="bg-gray-200 text-gray-700 px-3 py-1 rounded-lg text-xs">{{ t('Cancelar') }}</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="6" class="py-6 text-center text-gray-400">{{ t('Sem registos.') }}</td></tr>
            {% endfor %}
        </tbody>
    </table></div>
</div>
'''

HTML_ESTOQUE = '''
<div class="bg-white rounded-2xl border shadow-sm p-6">
    <h3 class="font-bold text-lg text-slate-900 mb-4">{{ t('Saldo en Tempo Real no Armazém') }}</h3>
    <div class="overflow-x-auto"><table class="w-full text-left"><thead><tr class="border-b text-xs text-gray-400 uppercase"><th class="pb-3">{{ t('Código') }}</th><th class="pb-3">{{ t('Material') }}</th><th class="pb-3">{{ t('Quantidade em Estoque') }}</th><th class="pb-3">{{ t('Estado') }}</th></tr></thead><tbody class="divide-y text-sm">
        {% for item in itens_estoque %}<tr class="hover:bg-gray-50"><td class="py-3 font-mono text-xs">{{ item.codigo_produto }}</td><td class="py-3 font-medium">{{ item.nome_material }}</td><td class="py-3 font-bold">{{ item.saldo_atual }} {{ item.unidade }}</td><td class="py-3">
        {% if item.saldo_atual <= item.stock_minimo %}<span class="px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-700">{{ t('Estoque Baixo') }}</span>{% else %}<span class="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">{{ t('Disponível') }}</span>{% endif %}</td></tr>{% else %}<tr><td colspan="4" class="py-6 text-center text-gray-400">{{ t('Nenhum material em estoque.') }}</td></tr>{% endfor %}
    </tbody></table></div>
</div>
'''

HTML_MOVIMENTOS = '''
<div class="bg-white rounded-2xl border shadow-sm p-6 mb-8">
    <h2 class="font-bold text-lg text-slate-900 mb-4">{{ t('Novo Movimento de Material') }}</h2>
    <form method="POST" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {% if session['perfil'] == 'admin' %}
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Tipo de Movimento') }}</label><select name="tipo_movimento" class="w-full rounded-xl border px-4 py-2.5 text-sm"><option value="Entrada">{{ t('Entrada') }}</option><option value="Saída">{{ t('Saída') }}</option></select></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Nome do Empregado') }}</label><input type="text" name="nome_empregado" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        {% else %}
        <input type="hidden" name="tipo_movimento" value="Saída">
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Nome do Empregado') }}</label><input type="text" name="nome_empregado" value="{{ session['nome'] }}" readonly class="w-full rounded-xl border bg-gray-50 px-4 py-2.5 text-sm"></div>
        {% endif %}
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Código do Produto') }}</label><input type="text" name="codigo_produto" class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Nome do Material') }}</label><input type="text" name="nome_material" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Quantidade') }}</label><input type="number" step="any" name="quantidade" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Unidade de Medida') }}</label><select name="unidade" class="w-full rounded-xl border px-4 py-2.5 text-sm"><option value="unidades">Unidades</option><option value="caixas">Caixas</option><option value="metros (m)">Metros (m)</option><option value="metros² (m²)">Metros² (m²)</option></select></div>
        <div class="lg:col-span-3"><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Obra / Destino') }}</label>
            <select name="obra" required class="w-full rounded-xl border px-4 py-2.5 text-sm">
                <option value="">-- {{ t('Selecione a Obra') }} --</option>
                {% for o in obras %}<option value="{{ o.nome }}">{{ o.nome }}</option>{% endfor %}
            </select>
        </div>
        <div class="lg:col-span-3 mt-2"><button type="submit" class="w-full bg-orange-600 text-white py-3 rounded-xl font-medium">{{ t('Registar Movimento') }}</button></div>
    </form>
</div>
<div class="bg-white rounded-2xl border shadow-sm p-6">
    <div class="flex justify-between items-center mb-4">
        <h3 class="font-bold text-lg text-slate-900">{{ t('Histórico de Movimentos') }}</h3>
        <a href="/exportar" class="bg-emerald-600 text-white px-4 py-2 rounded-xl text-xs font-bold flex items-center space-x-2"><i class="fa-solid fa-file-excel"></i><span>{{ t('Exportar Excel') }}</span></a>
    </div>
    <div class="overflow-x-auto"><table class="w-full text-left">
        <thead><tr class="border-b text-xs text-gray-400 uppercase"><th class="pb-3">{{ t('Data/Hora') }}</th><th class="pb-3">{{ t('Tipo') }}</th><th class="pb-3">{{ t('Código') }}</th><th class="pb-3">{{ t('Material') }}</th><th class="pb-3">{{ t('Qtd') }}</th><th class="pb-3">{{ t('Obra') }}</th></tr></thead>
        <tbody class="divide-y text-sm">
            {% for m in movimentos %}<tr class="hover:bg-gray-50"><td class="py-3 text-gray-500 text-xs">{{ m.data_hora }}</td><td class="py-3"><span class="px-2.5 py-1 rounded-full text-xs font-semibold {{ 'bg-green-100 text-green-700' if m.tipo_movimento == 'Entrada' else 'bg-red-100 text-red-700' }}">{{ t(m.tipo_movimento) }}</span></td><td class="py-3 text-gray-400 font-mono text-xs">{{ m.codigo_produto }}</td><td class="py-3">{{ m.nome_material }}</td><td class="py-3 font-semibold">{{ m.quantidade }} {{ m.unidade }}</td><td class="py-3 text-gray-500">{{ m.obra }}</td></tr>{% else %}<tr><td colspan="6" class="py-6 text-center text-gray-400">{{ t('Nenhum movimento registado.') }}</td></tr>{% endfor %}
        </tbody>
    </table></div>
</div>
'''

HTML_SOBRAS = '''
<div class="bg-white rounded-2xl border shadow-sm p-6 mb-8">
    <h2 class="font-bold text-lg text-slate-900 mb-4">{{ t('Registar Sobra (Entrada no Banco)') }}</h2>
    <form method="POST" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Material Disponível') }}</label><input type="text" name="material" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Quantidade') }}</label><input type="number" step="any" name="quantidade" required class="w-full rounded-xl border px-4 py-2.5 text-sm"></div>
        <div><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Unidade de Medida') }}</label><select name="unidade" class="w-full rounded-xl border px-4 py-2.5 text-sm"><option value="unidades">Unidades</option><option value="caixas">Caixas</option><option value="metros (m)">Metros (m)</option><option value="metros² (m²)">Metros² (m²)</option></select></div>
        <div class="md:col-span-3"><label class="block text-xs uppercase text-slate-500 mb-1">{{ t('Localização Atual / Obra') }}</label>
            <select name="localizacao_atual" required class="w-full rounded-xl border px-4 py-2.5 text-sm">
                {% for o in obras %}<option value="{{ o.nome }}">{{ o.nome }}</option>{% endfor %}
            </select>
        </div>
        <div class="md:col-span-3 mt-2"><button type="submit" class="w-full bg-indigo-600 text-white py-3 rounded-xl font-medium">{{ t('Disponibilizar Sobra para a Equipa') }}</button></div>
    </form>
</div>
<div class="bg-white rounded-2xl border shadow-sm p-6">
    <h3 class="font-bold text-lg text-slate-900 mb-4">{{ t('Banco de Sobras Ativas (Soma Total)') }}</h3>
    <div class="overflow-x-auto"><table class="w-full text-left">
        <thead><tr class="border-b text-xs text-gray-400 uppercase"><th class="pb-3">{{ t('Data') }}</th><th class="pb-3">{{ t('Material') }}</th><th class="pb-3">{{ t('Qtd Total') }}</th><th class="pb-3">{{ t('Local') }}</th><th class="pb-3">{{ t('Estado') }}</th><th class="pb-3" style="min-width: 320px;">{{ t('Ação') }}</th></tr></thead>
        <tbody class="divide-y text-sm">
            {% for s in sobras %}
            <tr class="hover:bg-gray-50">
                <td class="py-3 text-gray-500 text-xs">{{ s.data_hora }}</td>
                <td class="py-3 font-medium">{{ s.material }}</td>
                <td class="py-3 font-bold text-indigo-600">{{ s.quantidade }} {{ s.unidade }}</td>
                <td class="py-3 text-gray-500">{{ s.localizacao_atual }}</td>
                <td class="py-3"><span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700">{{ t(s.estado) }}</span></td>
                <td class="py-3">
                    <form action="/sobras/usar/{{ s.id }}" method="POST" class="flex items-center space-x-2">
                        <input type="number" step="any" name="quantidade_retirar" value="{{ s.quantidade }}" max="{{ s.quantidade }}" min="0.01" class="w-20 rounded-lg border px-2 py-1 text-xs" title="Qtd">
                        <select name="obra_destino" required class="rounded-lg border px-2 py-1 text-xs max-w-[140px]">
                            <option value="">-- Obra --</option>
                            {% for o in obras %}<option value="{{ o.nome }}">{{ o.nome }}</option>{% endfor %}
                        </select>
                        <button type="submit" class="bg-orange-50 hover:bg-orange-600 hover:text-white text-orange-600 px-3 py-1 rounded-lg text-xs font-semibold border border-orange-200 whitespace-nowrap">{{ t('Dar Baixa') }}</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr><td colspan="6" class="py-6 text-center text-gray-400">{{ t('Nenhuma sobra registada.') }}</td></tr>
            {% endfor %}
        </tbody>
    </table></div>
</div>
'''

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
