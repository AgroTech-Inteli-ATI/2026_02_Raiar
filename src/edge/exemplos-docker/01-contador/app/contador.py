"""Conta quantas vezes o container rodou e guarda o número em /dados."""
import os
from pathlib import Path

arquivo = Path("/dados/contagem.txt")
arquivo.parent.mkdir(parents=True, exist_ok=True)
n = int(arquivo.read_text()) + 1 if arquivo.exists() else 1
arquivo.write_text(str(n))
print(f"Olá! Esta é a execução número {n}. Sou o usuário {os.getuid()}.")
