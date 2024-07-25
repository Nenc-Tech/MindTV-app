# Projeto MindTV

O Projeto MindTV integra três funcionalidades principais: coleta de dados, treinamento de um modelo de aprendizado de máquina e previsão do tipo de conteúdo assistido com base em sensores GSR e de frequência cardíaca.

(`main-10p.py`)

### Funcionalidades:
- Coleta Inicial de Dados
- Seleção da porta serial
- Seleção do tipo de conteúdo assistido
- Definição da duração da coleta (1 a 5 minutos)
- Exibição em tempo real dos dados coletados
- Exportação dos dados coletados para um arquivo CSV
- Treinamento do Modelo
- Importação de até cinco arquivos CSV
- Treinamento de um modelo de aprendizado de máquina para prever o tipo de conteúdo
- Exibição dos logs de treinamento
- Previsão de Conteúdo
- Seleção da porta serial
- Definição da duração da coleta (1 a 5 minutos)
- Início da coleta de dados e exibição dos logs em tempo real
- Previsão do tipo de conteúdo usando o modelo treinado
- Exibição dos resultados da previsão


## Como a Rede Neural é Treinada
O treinamento da rede neural no Projeto MindTV é realizado na aba "Treinamento da Rede" através dos seguintes passos:

1. Importação dos Dados:

O usuário pode selecionar até cinco arquivos CSV para importar os dados. Cada arquivo deve conter as colunas irValue, beatsPerMinute, beatAvg, GSR e Content.
Os arquivos selecionados são combinados em um único DataFrame.

2. Pré-processamento dos Dados:

- A coluna irValue é ignorada durante o treinamento da rede, utilizando apenas as colunas beatsPerMinute, beatAvg e GSR como recursos (features).
- Os dados são separados em dois conjuntos: um para treinamento e outro para teste, utilizando a função train_test_split do Scikit-learn com uma divisão de 80% para treino e 20% para teste.
Treinamento do Modelo:

- Um modelo de RandomForestClassifier é inicializado e treinado com os dados de treinamento. O RandomForestClassifier é escolhido devido à sua robustez e capacidade de lidar bem com conjuntos de dados variados.
- O modelo é treinado utilizando os recursos beatsPerMinute, beatAvg e GSR, com o rótulo Content como a variável alvo.
Validação do Modelo:

- Após o treinamento, o modelo é avaliado utilizando o conjunto de dados de teste para garantir que ele generaliza bem para novos dados.
- Métricas como acurácia podem ser usadas para validar o desempenho do modelo, embora não estejam explicitamente mencionadas no código.
  
3. Salvar o Modelo:

- O modelo treinado é salvo em um arquivo trained_model.joblib utilizando a biblioteca joblib. Este modelo salvo é então usado na aba "Previsão de Conteúdo" para prever o tipo de conteúdo assistido com base nos dados coletados dos sensores.
- Este processo garante que o modelo de aprendizado de máquina esteja bem treinado e validado, pronto para realizar previsões precisas baseadas nos dados dos sensores GSR e de frequência cardíaca.
  

### Uso da aplicação:

### 1. Coleta Inicial 
1. Execute a interface:
     ```bash
        python main-10p.py

- Navegue até a aba "Coleta Inicial".
- Selecione a porta serial à qual o Arduino está conectado.
- Selecione o tipo de conteúdo assistido.
- Defina a duração da coleta (1 a 5 minutos).
- Clique em "Iniciar Coleta" para começar a coleta de dados.
- Monitore os dados em tempo real na área de log.
- Clique em "Exportar CSV" para salvar os dados coletados em um arquivo CSV.

### 2. Treinamento do Modelo:
- Navegue até a aba "Treinamento da Rede".
- Clique em "Selecionar arquivo CSV" para importar até cinco arquivos CSV.
- Clique em "Treinar Modelo" para iniciar o treinamento do modelo.
- Monitore os logs de treinamento na área de log.

### 3. Previsão de Conteúdo:
- Navegue até a aba "Previsão de Conteúdo".
- Selecione a porta serial à qual o Arduino está conectado.
- Defina a duração da coleta (1 a 5 minutos).
- Clique em "Iniciar Coleta" para começar a coleta de dados.
- Monitore os dados em tempo real na área de log.
- Clique em "Previsão de Conteúdo" para prever o tipo de conteúdo.
- Veja os resultados da previsão na nova janela de resultados.


## Dependências
Para o funcionamento correto do projeto MindTV, são necessárias as seguintes dependências:

- Python 3.x
- pandas
- scikit-learn
- PyQt5
- pyserial

## Instalação das Dependências

### Passo a Passo

1. **Certifique-se de que o Python 3.x está instalado:**
   Para verificar se o Python está instalado em seu sistema, você pode executar o seguinte comando no terminal:
   ```bash
   python --version

2. Crie um ambiente virtual (opcional, mas recomendado):
Para evitar conflitos entre pacotes, é recomendável criar um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate
````
3. Instale as dependências:
```bash
pip install -r requirements.txt
