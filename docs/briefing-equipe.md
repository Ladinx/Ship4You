como os dados reais do Olist sao mt grandes, quem precisa receber dados de outro integrante vai ter q criar uma tabelinha com numeros de exemplo dentro do proprio codigo só p testar se a logica funciona
quando cada um terminar sua parte, a gente substitui pelos dados reais e junta tudo

- O que entra no Vogel: 'custos' (matriz com o valor de cada rota), 'oferta' (lista com o que sai de cada origem) e 'demanda' (lista com o que cada destino precisa).
- O que sai do Vogel: 'alocacao' (matriz mostrando quantos produtos foram enviados em cada rota) e 'custo_total' (o valor final da operacao).

matheus - Modelagem de Dados e Matriz (arquivo: 'matriz_transporte.py')
Por que fazer: O algoritmo de Vogel nao le planilhas brutas, ele precisa receber os numeros ja organizados em listas e matrizes.
O que fazer:
- Usar os dados limpos da pasta 'dataset-tratado/' e evoluir o arquivo 'custo_rotas.py'.
- Agrupar os dados (por exemplo, por Estado/UF) para calcular quanto cada origem tem de 'oferta' e quanto cada destino precisa de 'demanda'.
- Gerar a matriz de 'custos' entre cada origem e cada destino.
- Garantir o balanceamento (se o total de oferta for diferente do total de demanda, criar uma linha ou coluna ficticia com custo zero para a conta fechar).
- Entrega final: Uma funcao que devolve 'custos', 'oferta' e 'demanda' prontos.

becca - Implementacao do Algoritmo de Vogel (arquivo: 'vogel.py')
Por que fazer: Esse e o motor matematico principal exigido no trabalho para encontrar o menor custo de transporte.
O que fazer:
- Programar o Metodo de Aproximacao de Vogel em Python.
- Calcular as penalidades das linhas e colunas, escolher a maior penalidade, alocar o maximo possivel na celula de menor custo e ir eliminando linhas e colunas que zerarem.
- Como os dados reais ainda estao sendo montados, criar uma matriz pequena com numeros de exemplo no final do arquivo so para testar e conferir na calculadora se o algoritmo esta acertando a conta.
- Entrega final: Uma funcao que recebe ('custos', 'oferta', 'demanda') e devolve ('alocacao', 'custo_total').

bender - Analise de Resultados e Graficos (arquivo: 'analise_resultados.py')
Por que fazer: Nao basta mostrar um numero solto no final; precisamos provar que o algoritmo de Vogel realmente economizou dinheiro em relacao ao frete real da Olist.
O que fazer:
- Calcular o custo total real que a Olist teve somando a coluna 'freight_value' do arquivo 'order_items_clean.csv' e comparar com o 'custo_total' gerado pelo Vogel (mostrando a economia em reais e em porcentagem).
- Criar graficos para a apresentacao (mapa de calor das rotas mais usadas, grafico de barras comparando Custo Real vs Custo Vogel e quais rotas ficaram sobrecarregadas).
- Enquanto o Vogel nao fica pronto com os dados reais, criar uma matriz 'alocacao' de exemplo no codigo para ja ir montando e testando o visual dos graficos.
- Entrega final: Uma funcao que recebe ('custos', 'alocacao', 'custo_total') e gera os graficos e o resumo dos numeros.

thur - Integracao, Execucao e Documentacao (arquivos: 'main.py' e 'README.md')
Por que fazer: Precisamos unir o trabalho dos outros tres em um unico lugar para o projeto rodar com um comando so e ficar bem explicado para quem avaliar.
O que fazer:
- Criar o 'main.py' que importa e executa os arquivos dos outros 3 integrantes na ordem certa (Matriz -> Vogel -> Graficos).
- Criar filtros simples antes de rodar (por exemplo, escolher filtrar por periodo ou categoria de produto) e gerar o arquivo 'requirements.txt' com as bibliotecas usadas.
- Atualizar o 'README.md' explicando como instalar e rodar o projeto, como o metodo de Vogel foi aplicado ao problema e quais foram os resultados obtidos.
