import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import sqlite3
from datetime import datetime

# ======================================================
# CAMADA DE DADOS (DATABASE & BACKEND)
# ======================================================

class BancoDeDados:
    def __init__(self):
        self.conn = sqlite3.connect("sorveteria.db")
        self.cursor = self.conn.cursor()
        self.criar_tabelas()

    def criar_tabelas(self):
        # MUDANÇA: Saiu 'preco', entrou 'qtd_por_caixa'
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                qtd_por_caixa INTEGER DEFAULT 1,
                estoque_total INTEGER DEFAULT 0
            )
        """)

        # ON DELETE CASCADE: Se apagar o produto, apaga o histórico dele para não dar erro
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER,
                tipo TEXT,
                qtd_caixas INTEGER,
                qtd_unidades INTEGER,
                data_hora TEXT,
                FOREIGN KEY(produto_id) REFERENCES produtos(id) ON DELETE CASCADE
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER,
                tipo TEXT,
                qtd_caixas INTEGER,
                qtd_unidades INTEGER,
                data_hora TEXT,
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        """)
        self.conn.commit()

    # --- NOVO: Função de Atualizar (Editar) ---
    def atualizar_produto(self, id_produto, novo_nome, nova_qtd_cx):
        self.cursor.execute("""
            UPDATE produtos 
            SET nome = ?, qtd_por_caixa = ? 
            WHERE id = ?
        """, (novo_nome, nova_qtd_cx, id_produto))
        self.conn.commit()

    # --- NOVO: Função de Excluir ---
    def excluir_produto(self, id_produto):
        # Primeiro exclui o histórico (movimentações) desse produto
        self.cursor.execute("DELETE FROM movimentacoes WHERE produto_id = ?", (id_produto,))
        # Depois exclui o produto
        self.cursor.execute("DELETE FROM produtos WHERE id = ?", (id_produto,))
        self.conn.commit()

    def cadastrar_produto(self, nome, qtd_por_caixa):
        self.cursor.execute("INSERT INTO produtos (nome, qtd_por_caixa) VALUES (?, ?)", (nome, qtd_por_caixa))
        self.conn.commit()

    def registrar_movimentacao(self, produto_id, tipo, caixas, unidades):
        # 1. Descobre quanto vale uma caixa para esse produto
        self.cursor.execute("SELECT qtd_por_caixa FROM produtos WHERE id = ?", (produto_id,))
        resultado = self.cursor.fetchone()
        
        if not resultado:
            raise ValueError("Produto não encontrado")
            
        tamanho_caixa = resultado[0]
        
        # 2. Converte tudo para unidade mínima (potes)
        total_movimentado = (caixas * tamanho_caixa) + unidades

        # 3. Registra histórico
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO movimentacoes (produto_id, tipo, qtd_caixas, qtd_unidades, data_hora)
            VALUES (?, ?, ?, ?, ?)
        """, (produto_id, tipo, caixas, unidades, data_atual))
        
        # 4. Atualiza o estoque total
        if tipo == "ENTRADA":
            sql_update = "UPDATE produtos SET estoque_total = estoque_total + ? WHERE id = ?"
        else: # SAIDA
            sql_update = "UPDATE produtos SET estoque_total = estoque_total - ? WHERE id = ?"
            
        self.cursor.execute(sql_update, (total_movimentado, produto_id))
        self.conn.commit()

    def listar_produtos(self):
       # MUDANÇA: Adicionado 'ORDER BY nome ASC' (Ordem Alfabética)
        self.cursor.execute("SELECT * FROM produtos ORDER BY nome ASC")
        return self.cursor.fetchall()

    def gerar_relatorio_mensal(self, mes, ano):
        filtro = f"{ano}-{mes}%"
        # Trazemos também o nome do produto para o relatório
        query = """
            SELECT p.nome, m.tipo, m.qtd_caixas, m.qtd_unidades, m.data_hora 
            FROM movimentacoes m
            JOIN produtos p ON m.produto_id = p.id
            WHERE m.data_hora LIKE ?
            ORDER BY m.data_hora DESC
        """
        self.cursor.execute(query, (filtro,))
        return self.cursor.fetchall()

# ======================================================
# CAMADA DE INTERFACE (GUI)
# ======================================================

class AppSorveteria:
    def __init__(self, root):
        self.db = BancoDeDados()
        self.root = root
        self.root.title("Sistema Sorveteria 2.0")
        # MUDANÇA 1: Abrir Maximizado (Tela Cheia)
        # O comando 'zoomed' funciona para Windows.
        try:
            self.root.state('zoomed')
        except:
            # Caso esteja no Linux/Mac, usa geometria grande
            self.root.geometry("1000x700")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Abas
        self.frame_cadastro = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_cadastro, text="Cadastro")
        
        self.frame_movim = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_movim, text="Entrada/Saída")
        
        self.frame_estoque = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_estoque, text="Gerenciar Estoque") # Nome mudou
        
        self.frame_relatorio = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_relatorio, text="Relatórios")

        self.montar_aba_cadastro()
        self.montar_aba_movimentacao()
        self.montar_aba_estoque()
        self.montar_aba_relatorio()

        self.notebook.bind("<<NotebookTabChanged>>", self.ao_mudar_aba)

    # --- CADASTRO ---
    def montar_aba_cadastro(self):
        ttk.Label(self.frame_cadastro, text="Nome do Produto:").pack(pady=5)
        self.entry_nome = ttk.Entry(self.frame_cadastro, width=40)
        self.entry_nome.pack(pady=5)

        ttk.Label(self.frame_cadastro, text="Padrão de Caixa (Qtd Potes):").pack(pady=5)
        self.entry_cx_tam = ttk.Entry(self.frame_cadastro)
        self.entry_cx_tam.insert(0, "1")
        self.entry_cx_tam.pack(pady=5)

        ttk.Button(self.frame_cadastro, text="Salvar Produto", command=self.acao_salvar_produto).pack(pady=20)

    def acao_salvar_produto(self):
        nome = self.entry_nome.get()
        cx_tam = self.entry_cx_tam.get()
        if nome and cx_tam:
            try:
                self.db.cadastrar_produto(nome, int(cx_tam))
                messagebox.showinfo("Sucesso", f"{nome} cadastrado!")
                self.entry_nome.delete(0, tk.END)
            except ValueError:
                messagebox.showerror("Erro", "Tamanho da caixa deve ser número.")
        else:
            messagebox.showwarning("Atenção", "Preencha todos os campos.")

    # --- MOVIMENTAÇÃO ---
    def montar_aba_movimentacao(self):
        ttk.Label(self.frame_movim, text="Produto:").pack(pady=5)
        self.combo_produtos = ttk.Combobox(self.frame_movim, width=40)
        self.combo_produtos.pack(pady=5)

        ttk.Label(self.frame_movim, text="Tipo:").pack(pady=5)
        self.combo_tipo = ttk.Combobox(self.frame_movim, values=["ENTRADA", "SAIDA"])
        self.combo_tipo.pack(pady=5)

        frame_qtd = ttk.Frame(self.frame_movim)
        frame_qtd.pack(pady=10)

        lbl_cx = ttk.Label(frame_qtd, text="Qtd Caixas:")
        lbl_cx.grid(row=0, column=0, padx=5)
        self.entry_qtd_cx = ttk.Entry(frame_qtd, width=10)
        self.entry_qtd_cx.insert(0, "0")
        self.entry_qtd_cx.grid(row=1, column=0, padx=5)

        lbl_un = ttk.Label(frame_qtd, text="Qtd Unidades Soltas:")
        lbl_un.grid(row=0, column=1, padx=5)
        self.entry_qtd_un = ttk.Entry(frame_qtd, width=10)
        self.entry_qtd_un.insert(0, "0")
        self.entry_qtd_un.grid(row=1, column=1, padx=5)

        ttk.Button(self.frame_movim, text="Registrar", command=self.acao_registrar_mov).pack(pady=20)

    def acao_registrar_mov(self):
        selecao = self.combo_produtos.get()
        tipo = self.combo_tipo.get()
        cx = self.entry_qtd_cx.get()
        un = self.entry_qtd_un.get()

        if selecao and tipo:
            try:
                id_prod = int(selecao.split(' | ')[0])
                qtd_cx = int(cx) if cx else 0
                qtd_un = int(un) if un else 0
                if qtd_cx == 0 and qtd_un == 0:
                     messagebox.showwarning("Erro", "Digite quantidade.")
                     return
                self.db.registrar_movimentacao(id_prod, tipo, qtd_cx, qtd_un)
                messagebox.showinfo("Sucesso", "Registrado!")
                self.entry_qtd_cx.delete(0, tk.END); self.entry_qtd_cx.insert(0, "0")
                self.entry_qtd_un.delete(0, tk.END); self.entry_qtd_un.insert(0, "0")
            except ValueError:
                messagebox.showerror("Erro", "Erro nos valores.")
        else:
            messagebox.showwarning("Erro", "Selecione produto e tipo.")

    # --- ESTOQUE (COM EDITAR E EXCLUIR) ---
    def montar_aba_estoque(self):
        # Botões de Ação no Topo
        frame_botoes = ttk.Frame(self.frame_estoque)
        frame_botoes.pack(pady=10)
        
        ttk.Button(frame_botoes, text="Atualizar Lista", command=self.carregar_estoque).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botoes, text="Editar Selecionado", command=self.janela_editar).pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_botoes, text="Excluir Selecionado", command=self.acao_excluir).pack(side=tk.LEFT, padx=5)

        # Tabela
        colunas = ('ID', 'Produto', 'Padrão cx', 'Visual', 'Total Unid.')
        self.tree_estoque = ttk.Treeview(self.frame_estoque, columns=colunas, show='headings')
        
        self.tree_estoque.heading('ID', text='ID')
        self.tree_estoque.heading('Produto', text='Produto')
        self.tree_estoque.heading('Padrão cx', text='Padrão cx')
        self.tree_estoque.heading('Visual', text='Estoque Visual')
        self.tree_estoque.heading('Total Unid.', text='Total')
        
        self.tree_estoque.column('ID', width=30)
        self.tree_estoque.column('Padrão cx', width=80)
        self.tree_estoque.column('Visual', width=200)
        
        self.tree_estoque.pack(fill='both', expand=True, padx=10, pady=10)

    def carregar_estoque(self):
        for item in self.tree_estoque.get_children():
            self.tree_estoque.delete(item)
        produtos = self.db.listar_produtos()
        for p in produtos:
            p_id, p_nome, p_padrao, p_total = p
            caixas = p_total // p_padrao if p_padrao > 0 else 0
            soltos = p_total % p_padrao if p_padrao > 0 else p_total
            visual = f"{caixas} Cxs e {soltos} Unid."
            self.tree_estoque.insert('', tk.END, values=(p_id, p_nome, p_padrao, visual, p_total))

    def acao_excluir(self):
        selecionado = self.tree_estoque.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um produto na lista para excluir.")
            return
        
        item = self.tree_estoque.item(selecionado[0])
        id_prod = item['values'][0]
        nome_prod = item['values'][1]

        confirmar = messagebox.askyesno("Confirmar Exclusão", 
                                        f"Tem certeza que deseja apagar '{nome_prod}'?\nIsso apagará também o histórico dele.")
        if confirmar:
            self.db.excluir_produto(id_prod)
            self.carregar_estoque()
            messagebox.showinfo("Sucesso", "Produto excluído.")

    def janela_editar(self):
        selecionado = self.tree_estoque.selection()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um produto para editar.")
            return

        item = self.tree_estoque.item(selecionado[0])
        id_prod = item['values'][0]
        nome_atual = item['values'][1]
        padrao_atual = item['values'][2]

        # Criar Janela Popup (Toplevel)
        janela_edit = Toplevel(self.root)
        janela_edit.title("Editar Produto")
        janela_edit.geometry("300x200")

        ttk.Label(janela_edit, text="Nome:").pack(pady=5)
        ent_nome = ttk.Entry(janela_edit, width=30)
        ent_nome.insert(0, nome_atual)
        ent_nome.pack(pady=5)

        ttk.Label(janela_edit, text="Padrão Caixa:").pack(pady=5)
        ent_padrao = ttk.Entry(janela_edit)
        ent_padrao.insert(0, padrao_atual)
        ent_padrao.pack(pady=5)

        def salvar_edicao():
            try:
                novo_nome = ent_nome.get()
                novo_padrao = int(ent_padrao.get())
                self.db.atualizar_produto(id_prod, novo_nome, novo_padrao)
                self.carregar_estoque() # Atualiza a lista principal
                janela_edit.destroy() # Fecha a janelinha
                messagebox.showinfo("Sucesso", "Produto atualizado!")
            except ValueError:
                messagebox.showerror("Erro", "Padrão deve ser número.")

        ttk.Button(janela_edit, text="Salvar Alterações", command=salvar_edicao).pack(pady=20)

    # --- RELATÓRIO ---
    def montar_aba_relatorio(self):
        frame_filtro = ttk.Frame(self.frame_relatorio)
        frame_filtro.pack(pady=10)
        
        ttk.Label(frame_filtro, text="Mês/Ano:").pack(side=tk.LEFT)
        self.entry_mes = ttk.Entry(frame_filtro, width=5); self.entry_mes.pack(side=tk.LEFT)
        self.entry_ano = ttk.Entry(frame_filtro, width=8); self.entry_ano.pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_filtro, text="Gerar", command=self.acao_gerar_relatorio).pack(side=tk.LEFT)

        colunas = ('Produto', 'Tipo', 'Caixas', 'Soltos', 'Data')
        self.tree_relatorio = ttk.Treeview(self.frame_relatorio, columns=colunas, show='headings')
        for col in colunas: self.tree_relatorio.heading(col, text=col)
        self.tree_relatorio.pack(fill='both', expand=True, padx=10, pady=10)

    def acao_gerar_relatorio(self):
        mes = self.entry_mes.get().zfill(2)
        ano = self.entry_ano.get()
        registros = self.db.gerar_relatorio_mensal(mes, ano)
        for item in self.tree_relatorio.get_children(): self.tree_relatorio.delete(item)
        for r in registros: self.tree_relatorio.insert('', tk.END, values=r)

    def atualizar_lista_combo(self):
        produtos = self.db.listar_produtos()
        self.combo_produtos['values'] = [f"{p[0]} | {p[1]}" for p in produtos]

    def ao_mudar_aba(self, event):
        self.atualizar_lista_combo()
        self.carregar_estoque()

if __name__ == "__main__":
    root = tk.Tk()
    app = AppSorveteria(root)
    root.mainloop()