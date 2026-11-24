"""
caminhos.py — resolução de caminhos do projeto.

A raiz do projeto é a pasta que contém `src/`, `dados/`, `saidas/` e `dashboard/`.
Assim o pipeline roda igual de qualquer diretório:

    python3 src/main.py            # da raiz
    python3 main.py                # de dentro de src/

Caminhos relativos que já existem no diretório atual são respeitados (útil para
testar em outra pasta de dados); os demais são resolvidos a partir da raiz.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "dados"
SAIDAS = RAIZ / "saidas"


def resolver(caminho) -> str:
    """Devolve o caminho relativo ao diretório atual, se existir; senão, à raiz."""
    caminho = Path(caminho)
    if caminho.is_absolute():
        return str(caminho)
    if caminho.exists():
        return str(caminho)
    return str(RAIZ / caminho)


def dados(caminho=None) -> str:
    return str(DADOS) if caminho is None else resolver(caminho)


def saidas(caminho=None) -> str:
    return str(SAIDAS) if caminho is None else resolver(caminho)
