"""
Sistema de processamento de consultas booleanas e cálculo de relevância.

Observação:
- Aqui não chamamos métodos que NÃO existem na sua Trie.
- Para encontrar documentos de um termo, usamos o indexador.obter_postings(termo),
  que devolve {doc: tf}. A Trie continua sendo útil para presença e para percorrer termos,
  mas a avaliação da consulta usa os postings do indexador (mais direto).
"""

import re


class ProcessadorBusca:
    """
    Processa consultas booleanas (AND/OR + parênteses), calcula relevância por
    média de z-scores e gera snippets.
    """

    def __init__(self, indexador):
        self.indexador = indexador

    # ------------------- tokenização + normalização -------------------

    def _tokenizar_consulta(self, consulta: str) -> list[str]:
        """
        Tokeniza a consulta preservando AND/OR e parênteses.
        Obs.: por simplicidade, converto AND/OR para MAIÚSCULAS, termos ficam minúsculos.
        """
        tokens = []
        atual = ""
        em_aspas = False

        for ch in consulta:
            if ch == '"':
                em_aspas = not em_aspas
                if atual.strip():
                    tokens.append(atual.strip())
                    atual = ""
            elif ch in "()" and not em_aspas:
                if atual.strip():
                    tokens.append(atual.strip())
                    atual = ""
                tokens.append(ch)
            elif ch.isspace() and not em_aspas:
                if atual.strip():
                    tokens.append(atual.strip())
                    atual = ""
            else:
                atual += ch

        if atual.strip():
            tokens.append(atual.strip())

        # Normaliza: AND/OR em maiúsculas; termos ficam limpos e minúsculos
        resultado = []
        for t in tokens:
            if t.upper() in ("AND", "OR"):
                resultado.append(t.upper())
            elif t in ("(", ")"):
                resultado.append(t)
            else:
                termo = re.sub(r"[^\w\s]", "", t.lower())
                if termo:
                    resultado.append(termo)
        return resultado

    # ------------------- infixa -> RPN (shunting-yard) -------------------

    def _para_rpn(self, tokens: list[str]) -> list[str]:
        """
        Converte a lista de tokens para Notação Polonesa Reversa (RPN),
        o que facilita muito a avaliação.
        """
        saida = []
        pilha = []
        precedencia = {"OR": 1, "AND": 2}  # AND > OR

        for tok in tokens:
            if tok == "(":
                pilha.append(tok)
            elif tok == ")":
                while pilha and pilha[-1] != "(":
                    saida.append(pilha.pop())
                if pilha and pilha[-1] == "(":
                    pilha.pop()
            elif tok in ("AND", "OR"):
                while pilha and pilha[-1] != "(" and precedencia.get(pilha[-1], 0) >= precedencia[tok]:
                    saida.append(pilha.pop())
                pilha.append(tok)
            else:
                saida.append(tok)

        while pilha:
            saida.append(pilha.pop())

        return saida

    # ------------------- avaliação da expressão em RPN -------------------

    def _avaliar_rpn(self, rpn_tokens: list[str]) -> set[str]:
        """
        Avalia a expressão booleana usando conjuntos de documentos.
        Para um termo T, usamos indexador.obter_postings(T).keys() como conjunto de docs.
        """
        pilha: list[set[str]] = []

        for tok in rpn_tokens:
            if tok == "AND":
                if len(pilha) >= 2:
                    b = pilha.pop()
                    a = pilha.pop()
                    pilha.append(a & b)
            elif tok == "OR":
                if len(pilha) >= 2:
                    b = pilha.pop()
                    a = pilha.pop()
                    pilha.append(a | b)
            else:
                # termo de busca: pega os docs pelo postings do indexador
                docs = set(self.indexador.obter_postings(tok).keys())
                pilha.append(docs)

        return pilha[0] if pilha else set()

    # ------------------- API de alto nível -------------------

    def processar_consulta(self, consulta: str) -> list[str]:
        """
        Pipeline: tokeniza -> converte pra RPN -> avalia -> devolve lista de docs.
        """
        if not self.indexador.indice_carregado:
            return []

        try:
            tokens = self._tokenizar_consulta(consulta)
            rpn = self._para_rpn(tokens)
            docs = self._avaliar_rpn(rpn)
            return list(docs)
        except Exception as e:
            print(f"Erro ao processar consulta '{consulta}': {e}")
            return []

    def calcular_relevancia(self, documentos: list[str], consulta_original: str) -> list[dict]:
        """
        Relevância = média dos z-scores dos termos da consulta no documento.
        (Se sigma for 0, z-score daquele termo vira 0; média dos que tiverem valor.)
        """
        tokens = self._tokenizar_consulta(consulta_original)
        termos = [t for t in tokens if t not in ("AND", "OR", "(", ")")]

        resultados = []
        for doc in documentos:
            zscores = [self.indexador.calcular_zscore(t, doc) for t in termos]
            # média só dos z ≠ 0 (opção para evitar divisão por 0 quando nada aparece)
            z_validos = [z for z in zscores if z != 0]
            relevancia = sum(z_validos) / len(z_validos) if z_validos else 0.0
            resultados.append({
                "documento": doc,
                "relevancia": relevancia,
                "z_scores": zscores
            })

        resultados.sort(key=lambda x: x["relevancia"], reverse=True)
        return resultados

    def buscar(self, consulta: str) -> list[dict]:
        """
        Processa a consulta e devolve os resultados já ordenados por relevância.
        """
        docs = self.processar_consulta(consulta)
        return self.calcular_relevancia(docs, consulta)

    def gerar_snippet(self, documento: str, consulta: str, tamanho: int = 80) -> str:
        """
        Snippet = 80 chars antes e 80 depois do termo "encontrado mais cedo".
        (Uma heurística simples e suficiente pro TP.)
        """
        conteudo = self.indexador.documentos.get(documento, "")
        if not conteudo:
            return ""

        tokens = self._tokenizar_consulta(consulta)
        termos = [t for t in tokens if t not in ("AND", "OR", "(", ")")]

        melhor_pos = -1
        melhor_termo = ""
        txt_lower = conteudo.lower()

        for termo in termos:
            pos = txt_lower.find(termo.lower())
            if pos != -1 and (melhor_pos == -1 or pos < melhor_pos):
                melhor_pos = pos
                melhor_termo = termo

        if melhor_pos == -1:
            # nada encontrado → devolve começo do documento
            trecho = conteudo[: 2 * tamanho]
            return (trecho + "...") if len(conteudo) > 2 * tamanho else trecho

        ini = max(0, melhor_pos - tamanho)
        fim = min(len(conteudo), melhor_pos + len(melhor_termo) + tamanho)
        trecho = conteudo[ini:fim]

        # destaca todos os termos (case-insensitive)
        for termo in termos:
            trecho = re.sub(rf"({re.escape(termo)})", r"<mark>\1</mark>", trecho, flags=re.IGNORECASE)

        if ini > 0:
            trecho = "..." + trecho
        if fim < len(conteudo):
            trecho = trecho + "..."

        return trecho
