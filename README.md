# SequenceSearchFlask

A web application built with Python and Flask that allows users to search, view, and manage sequences efficiently. This project demonstrates the integration of Python backend logic with a Flask-based web interface, providing a simple and interactive user experience.

Tutorial de instalação

1 - Clone o repositório em sua máquina.

2 - Ceritifique-se de possuir o Python 3.9+ instalado:

        python --version
        
Caso contrário instale:

        sudo apt update
        sudo apt install python3.9
        
3 - Crie um ambiente virtual com venv (Virtual Enviroment):

        python -m venv venv  
        
Ative o ambiente virtual:

        source venv/bin/activate     # Linux/macOS
        venv\Scripts\activate        # Windows
        
Deve-se criar ele apenas na primeira execução, mas deve ser ativado todas as vezes.

A utilização do venv é opcional, porém é uma boa prática que garante com que as dependências sejam isoladas, ou seja, as dependencias vão ser instaladas apenas neste ambiente e não vão interferir 
em outros projetos na sua máquina.

4 - Com o venv ativado, instale as dependências necessárias para o funcionamento do projeto (Flask):

        pip install -r requirements.txt 

5 - Para rodar o projeto:

        python app.py
        
Irá retornar o servidor em que o sistema está hospeado, basta abri-lo no navegador.
