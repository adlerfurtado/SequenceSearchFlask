from flask import Flask

# Criação da aplicação Flask 
app = Flask(__name__)   # __name__ é uma variável interna que marca o módulo atual


@app.route('/') # Quando o usuário acessa '/' (rota raiz), a função é chamada
def home(): 
    return "Olá, Flask! 🚀"


# Só roda o servidor se for executado diretamente e não importado como módulo
if __name__ == '__main__':
    app.run(debug=True) # Inicia o servidor Flask (modo debug para recarregar automaticamente)
