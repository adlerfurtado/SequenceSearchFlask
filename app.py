from flask import Flask, render_template, request
from indexador import IndexadorInvertido
from busca import ProcessadorBusca
import os
import time

# Criação da aplicação Flask (define pastas explicitamente)
app = Flask(__name__, template_folder="templates", static_folder="static")

# Configurações do sistema
CORPUS_PATH = "bbc"
INDICE_PATH = "indice.dat"

# Inicializa componentes (fica fora das rotas para reuso)
indexador = IndexadorInvertido()
processador_busca = ProcessadorBusca(indexador)
sistema_inicializado = False

def inicializar_sistema():
    """Carrega ou cria o índice apenas uma vez"""
    global sistema_inicializado
    if not sistema_inicializado:
        try:
            if indexador.carregar_indice(INDICE_PATH, CORPUS_PATH):
                print("Índice carregado!")
            else:
                print("Indexando corpus...")
                indexador.indexar_corpus(CORPUS_PATH)
                indexador.salvar_indice(INDICE_PATH)
            sistema_inicializado = True
        except Exception as e:
            print(f"Erro: {e}")

# ROTA DA HOME
@app.route('/')
def home():
    if not sistema_inicializado:
        inicializar_sistema()
    return render_template('home.html')

# ROTA DE RESULTADOS + paginação + tempo de busca
@app.route('/results')
def results():
    if not sistema_inicializado:
        inicializar_sistema()

    consulta = request.args.get('q', '').strip()
    pagina = int(request.args.get('page', 1))
    page_size = 10  # fixo

    if not consulta:
        return render_template(
            'results.html',
            resultados=[],
            consulta="",
            pagina=pagina,
            tam_pagina=page_size,
            total=0,
            duracao_ms=0.0
        )

    # Cronometra a busca
    t0 = time.perf_counter()
    resultados_brutos = processador_busca.buscar(consulta)
    duracao_ms = (time.perf_counter() - t0) * 1000.0

    # Paginação
    total = len(resultados_brutos)
    ini = max(0, (pagina - 1) * page_size)
    fim = min(ini + page_size, total)
    fatia = resultados_brutos[ini:fim]

    # Formata para o template
    resultados_formatados = []
    for r in fatia:
        doc_path = r['documento']
        resultados_formatados.append({
            'arquivo_path': os.path.relpath(doc_path, CORPUS_PATH),  # relativo pra URL
            'titulo': indexador.obter_titulo_documento(doc_path),
            'relevancia': f"{r['relevancia']:.4f}",
            'snippet': processador_busca.gerar_snippet(doc_path, consulta)
        })


    return render_template(
        'results.html',
        resultados=resultados_formatados,
        consulta=consulta,
        pagina=pagina,
        tam_pagina=page_size,
        total=total,
        duracao_ms=duracao_ms
    )

@app.route('/documento/<path:arquivo>')
def documento(arquivo):

    #Exibe o conteúdo completo de um documento
    
    caminho = os.path.join(CORPUS_PATH, arquivo)
    if not os.path.exists(caminho):
        return render_template('documento.html', titulo="Arquivo não encontrado", conteudo="")

    with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        conteudo = f.read()

    titulo = indexador.obter_titulo_documento(caminho)
    return render_template('documento.html', titulo=titulo, conteudo=conteudo)

# Executa o servidor Flask
if __name__ == '__main__':
    inicializar_sistema()
    app.run(debug=True)
