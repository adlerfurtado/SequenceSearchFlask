from flask import Flask, render_template

# Criação da aplicação Flask 
app = Flask(__name__)


@app.route('/')
def home():
    # Renderiza um arquivo HTML da pasta "templates"
    return render_template('home.html')

@app.route('/results')
def results():
    # Renderiza um arquivo HTML da pasta "templates"
    return render_template('results.html')


# Só roda o servidor se for executado diretamente e não importado como módulo
if __name__ == '__main__':
    app.run(debug=True) # Inicia o servidor Flask (modo debug para recarregar automaticamente)
