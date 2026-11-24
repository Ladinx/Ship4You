import numpy as np
from matriz_transporte import gerar_matriz_transporte

def resolver_vogel(custos, oferta, demanda):
    custos = np.array(custos, dtype=float)
    oferta = list(oferta)
    demanda = list(demanda)
    
    n_linhas = len(oferta)
    n_colunas = len(demanda)
    
    alocacao = np.zeros((n_linhas, n_colunas))
    linhas_ativas = [True] * n_linhas
    colunas_ativas = [True] * n_colunas

    while sum(oferta) > 0 and sum(demanda) > 0:
        penalidades_linhas = []
        penalidades_colunas = []
        
        for i in range(n_linhas):
            if linhas_ativas[i] and oferta[i] > 0:
                custos_linha = sorted([custos[i][j] for j in range(n_colunas) if colunas_ativas[j]])
                if len(custos_linha) >= 2:
                    penalidades_linhas.append((custos_linha[1] - custos_linha[0], 'L', i))
                elif len(custos_linha) == 1:
                    penalidades_linhas.append((custos_linha[0], 'L', i))
            elif linhas_ativas[i]:
                linhas_ativas[i] = False

        for j in range(n_colunas):
            if colunas_ativas[j] and demanda[j] > 0:
                custos_coluna = sorted([custos[i][j] for i in range(n_linhas) if linhas_ativas[i]])
                if len(custos_coluna) >= 2:
                    penalidades_colunas.append((custos_coluna[1] - custos_coluna[0], 'C', j))
                elif len(custos_coluna) == 1:
                    penalidades_colunas.append((custos_coluna[0], 'C', j))
            elif colunas_ativas[j]:
                colunas_ativas[j] = False

        todas_penalidades = penalidades_linhas + penalidades_colunas
        if not todas_penalidades:
            break 
            
        maior_penalidade = max(todas_penalidades, key=lambda x: x[0])
        tipo, index = maior_penalidade[1], maior_penalidade[2]

        if tipo == 'L': 
            linha = index
            colunas_validas = [j for j in range(n_colunas) if colunas_ativas[j]]
            coluna = min(colunas_validas, key=lambda j: custos[linha][j])
        else: 
            coluna = index
            linhas_validas = [i for i in range(n_linhas) if linhas_ativas[i]]
            linha = min(linhas_validas, key=lambda i: custos[i][coluna])

        quantidade = min(oferta[linha], demanda[coluna])
        alocacao[linha][coluna] += quantidade
        
        oferta[linha] -= quantidade
        demanda[coluna] -= quantidade

        if oferta[linha] == 0:
            linhas_ativas[linha] = False
        if demanda[coluna] == 0:
            colunas_ativas[coluna] = False

    custo_total = np.sum(alocacao * custos)
    return alocacao, custo_total


if __name__ == "__main__":
    custos_reais, oferta_real, demanda_real, origens, destinos, custo_real_historico = gerar_matriz_transporte()
    
    alocacao, custo_otimizado = resolver_vogel(custos_reais, oferta_real, demanda_real)
    
    print(f"Custo Histórico Real da Olist: R$ {custo_real_historico:,.2f}")
    print(f"Custo Otimizado pelo Vogel:    R$ {custo_otimizado:,.2f}")
    
    economia = custo_real_historico - custo_otimizado
    print(f"Economia gerada:               R$ {economia:,.2f}")