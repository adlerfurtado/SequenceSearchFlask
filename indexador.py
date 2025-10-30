"""
Sistema de indexação invertida usando Trie Compacta.
Responsável por processar documentos e construir o índice de busca.
"""

import os
import re
import math
import json
from collections import Counter, defaultdict
from trie import Trie


class IndexadorInvertido:

    #Sistema principal de indexação e recuperação de documentos.

    def __init__(self):
        self.trie = Trie()
        self.postings = defaultdict(dict)      # termo -> {doc: tf}
        self.documentos = {}                   # doc -> texto
        self.metadados_documentos = {}         # doc -> metadados simples
        self.estatisticas_globais = {
            "total_documentos": 0,
            "total_palavras": 0,
            "palavras_unicas": 0
        }
        self.indice_carregado = False

    # ---------- utilidades de processamento de texto ----------

    _RE_TOKEN = re.compile(r"[a-z0-9]+", re.IGNORECASE)

    def _normalizar(self, texto: str) -> str:
        """
        Deixa tudo minúsculo e troca pontuação por espaços.
        (Simples e suficiente para o TP; dá pra evoluir depois.)
        """
        return re.sub(r"[^\w\s]", " ", texto.lower())

    def _tokenizar(self, texto: str) -> list[str]:
        """
        Quebra o texto em palavras "válidas" (apenas letras/dígitos).
        Removo palavras com 1-2 letras porque tendem a ser muito ruidosas.
        """
        texto = self._normalizar(texto)
        tokens = self._RE_TOKEN.findall(texto)
        return [t for t in tokens if len(t) > 2]

    # ---------- indexação ----------

    def indexar_documento(self, caminho: str, conteudo: str):
        """
        Indexa um único documento:
        - quebra em palavras
        - atualiza Trie (presença)
        - atualiza postings (contagem tf)
        - armazena metadados
        """
        tokens = self._tokenizar(conteudo)

        # guarda texto bruto (para snippet)
        self.documentos[caminho] = conteudo

        # metadado básico, só pra ter algo útil no relatório/resultados
        self.metadados_documentos[caminho] = {
            "tamanho": len(conteudo),
            "num_palavras": len(tokens),
            "palavras_unicas": len(set(tokens))
        }

        # contagem por termo no documento
        tf_doc = Counter(tokens)

        # atualiza estruturas
        for termo, tf in tf_doc.items():
            # 1) presença na Trie (sua API atual pede termo + arquivo)
            self.trie.inserir(termo, caminho)
            # 2) contagem para ranking
            self.postings[termo][caminho] = self.postings[termo].get(caminho, 0) + tf

        # estatística global simples
        self.estatisticas_globais["total_documentos"] += 1
        self.estatisticas_globais["total_palavras"] += len(tokens)
    
    def obter_titulo_documento(self, caminho: str) -> str:
        """
        Retorna o título do documento (primeira linha ou nome do arquivo).
        """
        try:
            conteudo = self.documentos.get(caminho)
            if conteudo:
                # Pega a primeira linha não vazia como título
                for linha in conteudo.splitlines():
                    if linha.strip():
                        return linha.strip()
            # Se não achou, devolve o nome do arquivo
            return os.path.basename(caminho)
        except Exception:
            return os.path.basename(caminho)

    def indexar_corpus(self, pasta_corpus: str) -> int:
        """
        Percorre a pasta do corpus BBC e indexa todos os .txt.
        Estrutura esperada: bbc/<categoria>/*.txt
        """
        if not os.path.exists(pasta_corpus):
            raise FileNotFoundError(f"Pasta do corpus não encontrada: {pasta_corpus}")

        docs = 0
        categorias = ["business", "entertainment", "politics", "sport", "tech"]
        print("Iniciando indexação do corpus BBC...")

        for categoria in categorias:
            pasta = os.path.join(pasta_corpus, categoria)
            if not os.path.isdir(pasta):
                print(f"Aviso: pasta de categoria ausente: {categoria}")
                continue

            for nome in os.listdir(pasta):
                if not nome.lower().endswith(".txt"):
                    continue
                caminho = os.path.join(pasta, nome)
                try:
                    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                        conteudo = f.read().strip()
                    if conteudo:
                        self.indexar_documento(caminho, conteudo)
                        docs += 1
                        if docs % 100 == 0:
                            print(f"Documentos processados: {docs}")
                except Exception as e:
                    print(f"Erro ao processar {caminho}: {e}")

        # palavras únicas: simplesmente o número de chaves em postings
        self.estatisticas_globais["palavras_unicas"] = len(self.postings)
        self.indice_carregado = True
        print(f"Indexação concluída! {docs} documentos processados.")
        return docs

    # ---------- API para a busca ----------

    def obter_postings(self, termo: str) -> dict:
        """
        Retorna {documento: tf} para um termo.
        Se o termo não existir, devolve dicionário vazio.
        """
        return dict(self.postings.get(termo, {}))

    def calcular_zscore(self, termo: str, documento: str) -> float:
        """
        z-score = (tf_doc - média) / desvio_padrão
        onde média e desvio são calculados sobre os documentos em que o termo aparece.
        Se o termo não aparece em lugar nenhum (ou variância zero), retorna 0.
        """
        docs_tf = self.postings.get(termo, {})
        if not docs_tf:
            return 0.0

        valores = list(docs_tf.values())
        media = sum(valores) / len(valores)
        # variância populacional
        var = sum((v - media) ** 2 for v in valores) / len(valores)
        desvio = math.sqrt(var) if var > 0 else 0.0

        tf_doc = docs_tf.get(documento, 0)
        if desvio == 0.0:
            return 0.0
        return (tf_doc - media) / desvio

    # ---------- persistência em formato próprio (texto) ----------

    def salvar_indice(self, caminho_arquivo: str):
        """
        Salva tudo em um arquivo texto simples com seções.
        Formato:
          # ESTATISTICAS_GLOBAIS
          <json das estatísticas>
          # METADADOS_DOCUMENTOS
          <json dos metadados por doc>
          # DOCUMENTOS
          <json lista com caminhos de docs>
          # POSTINGS
          termo|doc1:tf1;doc2:tf2;...
        """
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write("# ESTATISTICAS_GLOBAIS\n")
            f.write(json.dumps(self.estatisticas_globais) + "\n")

            f.write("# METADADOS_DOCUMENTOS\n")
            f.write(json.dumps(self.metadados_documentos) + "\n")

            f.write("# DOCUMENTOS\n")
            f.write(json.dumps(list(self.documentos.keys())) + "\n")

            f.write("# POSTINGS\n")
            for termo in sorted(self.postings.keys()):
                pares = ";".join(f"{doc}:{tf}" for doc, tf in sorted(self.postings[termo].items()))
                f.write(f"{termo}|{pares}\n")

        print(f"Índice salvo em: {caminho_arquivo}")

    def carregar_indice(self, caminho_arquivo: str, pasta_corpus: str) -> bool:
        """
        Lê o arquivo de índice e reconstrói:
          - postings (com tf)
          - presença na Trie (inserindo uma única vez por doc, pois ela só guarda presença)
          - documentos (conteúdo bruto) para snippet
        """
        if not os.path.exists(caminho_arquivo):
            return False

        try:
            self.trie = Trie()
            self.postings = defaultdict(dict)
            self.documentos = {}
            self.metadados_documentos = {}
            self.estatisticas_globais = {
                "total_documentos": 0,
                "total_palavras": 0,
                "palavras_unicas": 0
            }

            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                linhas = [ln.rstrip("\n") for ln in f]

            modo = None
            docs_list = []

            for linha in linhas:
                if not linha or linha.startswith("#"):
                    if linha == "# ESTATISTICAS_GLOBAIS":
                        modo = "est"
                    elif linha == "# METADADOS_DOCUMENTOS":
                        modo = "meta"
                    elif linha == "# DOCUMENTOS":
                        modo = "docs"
                    elif linha == "# POSTINGS":
                        modo = "postings"
                    continue

                if modo == "est":
                    self.estatisticas_globais = json.loads(linha)
                elif modo == "meta":
                    self.metadados_documentos = json.loads(linha)
                elif modo == "docs":
                    docs_list = json.loads(linha)
                elif modo == "postings":
                    termo, serial = linha.split("|", 1)
                    if serial:
                        for par in serial.split(";"):
                            doc, tf = par.split(":")
                            tf = int(tf)
                            self.postings[termo][doc] = tf
                            # presença na Trie: uma única inserção por doc é suficiente
                            self.trie.inserir(termo, doc)

            # carrega os conteúdos dos documentos (para snippet)
            for caminho in docs_list:
                try:
                    with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                        self.documentos[caminho] = f.read()
                except Exception as e:
                    # se algum arquivo sumiu, seguimos em frente
                    print(f"Aviso: não consegui abrir {caminho}: {e}")

            # se por algum motivo não veio no arquivo, garantimos estes dois números:
            self.estatisticas_globais["total_documentos"] = max(
                self.estatisticas_globais.get("total_documentos", 0),
                len(self.metadados_documentos) or len(docs_list)
            )
            self.estatisticas_globais["palavras_unicas"] = len(self.postings)

            self.indice_carregado = True
            print("Índice carregado com sucesso.")
            return True

        except Exception as e:
            print(f"Erro ao carregar índice: {e}")
            return False
