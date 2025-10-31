#Sistema de processamento de consultas booleanas e cálculo de relevância

import re


class ProcessadorBusca:
    
    #Processa consultas booleanas (AND/OR + parênteses), calcula relevância por média de z-scores e gera snippets.
    

    def __init__(self, indexador):
        # guardamos a referência do indexador para consultar postings, z-score etc
        self.indexador = indexador

    # tokenização + normalização 

    def _tokenizar_consulta(self, consulta: str) -> list[str]:
        
        #Tokeniza a consulta preservando AND/OR e parênteses
        #AND/OR ficam em MAIÚSCULAS
        #termos ficam minúsculos e sem pontuação
        #**extra**: insere AND implícito entre termos adjacentes
        
        tokens = []
        atual = ""
        em_aspas = False

        # varre caractere a caractere para respeitar aspas e parênteses
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

        # normaliza (AND/OR maiúsculos; termos minúsculos sem pontuação)
        normalizados: list[str] = []
        for t in tokens:
            if t.upper() in ("AND", "OR"):
                normalizados.append(t.upper())
            elif t in ("(", ")"):
                normalizados.append(t)
            else:
                termo = re.sub(r"[^\w\s]", "", t.lower())
                if termo:
                    normalizados.append(termo)

        # insere AND implícito entre termos adjacentes
        # regra: se token atual é termo/")" e o próximo é termo/"("
        corrigidos: list[str] = []
        for i, t in enumerate(normalizados):
            corrigidos.append(t)
            if i < len(normalizados) - 1:
                prox = normalizados[i + 1]
                # Se o token atual é termo/")" e o próximo é termo/"(", então falta um AND
                cond_atual_e_termo = t not in ("AND", "OR", "(", ")")
                cond_prox_termo_ou_abre = prox not in ("AND", "OR", ")")
                if cond_atual_e_termo and cond_prox_termo_ou_abre:
                    corrigidos.append("AND")

        return corrigidos

    # infixa -> RPN (shunting-yard) 

    def _para_rpn(self, tokens: list[str]) -> list[str]:
        
        #Converte a expressão infixa para Notação Polonesa Reversa (RPN)
        
        saida = []
        pilha = []
        precedencia = {"OR": 1, "AND": 2}  # AND tem maior precedência

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

    # avaliação da expressão em RPN 

    def _avaliar_rpn(self, rpn_tokens: list[str]) -> set[str]:
        
        #Avalia a expressão booleana usando conjuntos de documentos
        
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
                # termo de busca -> conjunto de docs onde ele aparece
                docs = set(self.indexador.obter_postings(tok).keys())
                pilha.append(docs)

        return pilha[0] if pilha else set()

    # API de alto nível

    def processar_consulta(self, consulta: str) -> list[str]:
        
        #Pipeline: tokeniza -> converte pra RPN -> avalia -> devolve lista de docs
        
        if not self.indexador.indice_carregado:
            return []

        try:
            tokens = self._tokenizar_consulta(consulta)
            rpn = self._para_rpn(tokens)
            docs = self._avaliar_rpn(rpn)
            return list(docs)
        except Exception as e:
            # não interrompe o servidor se a consulta for inválida
            print(f"Erro ao processar consulta '{consulta}': {e}")
            return []

    def calcular_relevancia(self, documentos: list[str], consulta_original: str) -> list[dict]:
        
        #Relevância = média dos z-scores dos termos da consulta no documento
        #(Se sigma for 0, z-score daquele termo vira 0; média dos que tiverem valor)
        
        tokens = self._tokenizar_consulta(consulta_original)
        termos = [t for t in tokens if t not in ("AND", "OR", "(", ")")]

        resultados = []
        for doc in documentos:
            zscores = [self.indexador.calcular_zscore(t, doc) for t in termos]
            z_validos = [z for z in zscores if z != 0]
            relevancia = sum(z_validos) / len(z_validos) if z_validos else 0.0
            resultados.append({
                "documento": doc,
                "relevancia": relevancia,
                "z_scores": zscores
            })

        # maior relevância primeiro
        resultados.sort(key=lambda x: x["relevancia"], reverse=True)
        return resultados

    def buscar(self, consulta: str) -> list[dict]:
        
        #Processa a consulta e devolve os resultados já ordenados por relevância
        
        docs = self.processar_consulta(consulta)
        return self.calcular_relevancia(docs, consulta)

    def gerar_snippet(self, documento: str, consulta: str, tamanho: int = 80) -> str:
        
        #Snippet = 80 caracteres antes e 80 depois do primeiro termo encontrado
        
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
            # se nada for encontrado → devolve começo do documento
            trecho = conteudo[: 2 * tamanho]
            return (trecho + "...") if len(conteudo) > 2 * tamanho else trecho

        ini = max(0, melhor_pos - tamanho)
        fim = min(len(conteudo), melhor_pos + len(melhor_termo) + tamanho)
        trecho = conteudo[ini:fim]

        # destaca todos os termos 
        for termo in termos:
            trecho = re.sub(rf"({re.escape(termo)})", r"<mark>\1</mark>", trecho, flags=re.IGNORECASE)

        if ini > 0:
            trecho = "..." + trecho
        if fim < len(conteudo):
            trecho = trecho + "..."

        return trecho
