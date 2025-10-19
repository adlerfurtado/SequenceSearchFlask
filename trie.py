# Trie compacta
# Guarda prefixo das chaves comuns
# Valores apenas nas folhas

class Node:
    # Construtor do nó  
    def __init__(self): 
        self.filhos = {} # Todos os filhos do nó
        self.arquivos = set() # Arquivos em que o padrao aparece
        self.folha = False # Indica se é folha, consequentemente se tem valor


class Trie:
     # Construtor da Trie
    def __init__(self):
        self.raiz = Node() # Inicia com o nó raiz nulo

    # Retorna comprimento do prefixo comum entre a e b
    def tam_prefixo_comum(self, a: str, b: str) -> int:
        i = 0
        limite = min(len(a), len(b)) # retoorna o menor tamanho entre a e b
        while i < limite and a[i] == b[i]:
            i += 1
        return  i

    # Insere padrao associado a um arquivo na Trie
    def inserir(self, padrao: str, arquivo: str):
        # Inicia a partir da raiz
        node = self.raiz
        # Vai consumindo o padrão até não restar nada
        while padrao:
            # Itera sobre as chaves atuais.
            for chave in list(node.filhos.keys()): # Lista todos os filhos do nó atual
                comum = self.tam_prefixo_comum(chave, padrao)
                # Se não tem nenhum prefixo comum, pula pro proximo filho da lista
                if comum == 0:
                    continue

                # Caso 1: o nó atual é prefixo do padrao (ex: chave="ca", padrao="casa")
                if comum == len(chave):
                    padrao = padrao[comum:]  # Consome o prefixo comum do padrao ex: "casa -> "sa"/pega os ultimos "comum" caracteres
                    node = node.filhos[chave] # Desce o nó de análise para o proximo nível
                    break  # volta ao while externo para continuar com o resto do padrao, funciona pois agora o nó foi atualizado

                # Caso 2: o padrao é prefixo do nó atual (ex: chave="casa", padrao="ca")
                # Divide o nó atual em dois nós, chave = prefixo comum + resto do padrão
                prefixo_comum = chave[:comum]           
                restante_chave = chave[comum:]

                # Realoca o filho existente sob um novo nó intermediário
                filho_existente = node.filhos.pop(chave)  # Remove a chave antiga (lembrando que estamos o nó é a raiz)
                novo_no = Node() # Cria um novo nó intermediário
                novo_no.filhos[restante_chave] = filho_existente # filho_existente agora é só a parte não comum
                node.filhos[prefixo_comum] = novo_no # raiz agora aponta pro nó intermediario "ca"

                padrao_resto = padrao[comum:] # Tira também o prefixo comum do padrão

                if padrao_resto == "": # Padrão foi consumido = adiciona valor
                    novo_no.folha = True
                    novo_no.arquivos.add(arquivo)
                else:
                    # Se ainda resta parte do padrão, adocopma e, novo nó filho
                    no_filho_do_padrao = Node()
                    no_filho_do_padrao.folha = True
                    no_filho_do_padrao.arquivos.add(arquivo)
                    novo_no.filhos[padrao_resto] = no_filho_do_padrao
                return  

            else:
                # Caso 3 = Não tem prefixo comum com os filhos -> novo nó com o restante do padrao
                novo = Node()
                novo.folha = True
                novo.arquivos.add(arquivo)
                node.filhos[padrao] = novo # Adicionsa o novo nó como filho da raiz
                return

        # Se chega aqui é porque o padrão foi consumido completamente
        node.folha = True
        node.arquivos.add(arquivo)

    # Remove padrao associado a um arquivo da Trie (recursivamente)
    def remover(self, padrao: str, arquivo: str):
        # Função recursiva: retorna True se o padrão foi removido
        def pode_remover(node, padrao):
            for chave, filho in list(node.filhos.items()):  # Itera sobre os filhos
                comum = self.tam_prefixo_comum(chave, padrao)

                # Se não tem prefixo comum, passa pro próximo filho
                if comum == 0:
                    continue

                # Se o prefixo em comum é menor que padrão e que a chave então não tem valor associado
                if comum < len(chave) and comum < len(padrao):
                    return False

                # Padrão foi totalmente consumido no nó atual
                elif comum == len(padrao) and comum <= len(chave):
                    if arquivo in filho.arquivos:
                        filho.arquivos.remove(arquivo)

                    # Se não tem mais arquivos associados tira o valor associado
                    if not filho.arquivos:
                        filho.folha = False

                    # Remove o nó se ele estiver completamente vazio
                    if not filho.filhos and not filho.folha:
                        node.filhos.pop(chave)

                    return True  # Padrão removido 

                # Padrão continua no filho
                elif comum == len(chave) and comum < len(padrao): # Ou seja o padrão é maior que a chave do nó
                    padrao_resto = padrao[comum:]
                    removido = pode_remover(filho, padrao_resto)

                    # Verifica se todos os filhos do nó filho foram removidos e se tem valor associado
                    if removido and not filho.filhos and not filho.folha:
                        node.filhos.pop(chave)

                    return removido

            # Nenhum filho tem prefixo comum com o padrão
            return False

        # Remove começando da raiz e retorna se deu certo
        return pode_remover(self.raiz, padrao)