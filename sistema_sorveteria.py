import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

# Configuração do banco de dados

class BancoDeDados:
    def __init__(self):
        self.conexao = sqlite3.connect('sorveteria.db')
        self.cursor = self.conexao.cursor()
        self.criar_tabelas()

    def criar_tabelas(self):
        #tabela de produtos
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL
                estoque INTEGER DEFAULT 0
            )
        ''')
        #tabela de movimentações 
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER,
                tipo TEXT, -- 'entrada' ou 'saida'
                quantidade INTEGER,
                total REAL,
                data TEXT,
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        self.conexao.commit()

        def cadastrar_produto(self, nome, preco, estoque):
            self.cursor.execute('''
                INSERT INTO produtos (nome, preco, estoque) VALUES (?, ?, ?)
            ''', (nome, preco, estoque))
            self.conexao.commit()

            def registrar_movimentacao(self, produto_id, tipo, quantidade, total):
                # Registrar a movimentação no banco de dados
                data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.cursor.execute('''
                    INSERT INTO movimentacoes (produto_id, tipo, quantidade, total, data) VALUES (?, ?, ?, ?, ?)
                ''', (produto_id, tipo, quantidade, total, data_atual))

                # Atualizar o estoque do produto
                if tipo == 'entrada':
                    sql_update = 'UPDATE produtos SET estoque = estoque + ? WHERE id = ?'
                else: #saida
                    sql_update = 'UPDATE produtos SET estoque = estoque - ? WHERE id = ?'

                self.cursor.execute(sql_update, (quantidade, produto_id))
                self.conexao.commit()

                def listar_produtos(self):
                    self.cursor.execute('SELECT id, nome, preco, estoque FROM produtos')
                    return self.cursor.fetchall()
                
                def gerar_relatorio_mensal(self, mes, ano):
                    # ex: filtra onde a data comeca com o mes e ano selecionados

                    filtro = f'{ano}-{mes:02d}%'  # Formato 'YYYY-MM%'

                    query = '''
                        SELECT p.nome, m.tipo, m.quantidade, m.total, m.data
                        FROM movimentacoes m
                        JOIN produtos p ON m.produto_id = p.id
                        WHERE m.data LIKE ?
                        ORDER BY m.data DESC
                    '''
                    self.cursor.execute(query, (filtro,))
                    return self.cursor.fetchall()
                
                def fechar_conexao(self):
                    self.conexao.close()