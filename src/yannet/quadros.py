"""Extrai os quadros de desenvolvimento e prepara o pacote opcional do Colab."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import cv2

PASTA = Path(__file__).resolve().parent
MIDIAS = PASTA.parent / "raiarnet" / "img"
SAIDA = PASTA / "outputs" / "desenvolvimento"

VIDEOS = {
    "c1-dia": "WhatsApp Video 2026-09-29 at 12.02.03.mp4",
    "c1-ir": "WhatsApp Video 2026-09-29 at 12.02.02.mp4",
    "cam16-cria": "WhatsApp Video 2026-10-09 at 10.45.21.mp4",
    "cam16-externa": "WhatsApp Video 2026-09-29 at 12.02.02 (1).mp4",
}
AMOSTRAS = (
    ("c1-dia", 2),
    ("c1-ir", 2),
    ("cam16-cria", 120),
    ("c1-dia", 6),
    ("c1-dia", 9),
    ("c1-dia", 11),
    ("c1-ir", 7),
    ("c1-ir", 13),
    ("cam16-cria", 20),
    ("cam16-cria", 300),
    ("cam16-externa", 2),
    ("cam16-externa", 8),
)


def extrair_quadro(caminho, segundo):
    captura = cv2.VideoCapture(str(caminho))
    try:
        fps = captura.get(cv2.CAP_PROP_FPS)
        if not captura.isOpened() or fps <= 0:
            raise ValueError(f"Não foi possível abrir {caminho} como vídeo.")
        indice = round(segundo * fps)
        if not captura.set(cv2.CAP_PROP_POS_FRAMES, indice):
            raise ValueError(f"Não foi possível posicionar {caminho} em {segundo} s.")
        ok, quadro = captura.read()
        if not ok:
            raise ValueError(f"Não foi possível extrair o quadro de {caminho} em {segundo} s.")
        return quadro, indice, captura.get(cv2.CAP_PROP_POS_MSEC) / 1000
    finally:
        captura.release()


def preparar(saida):
    saida.mkdir(parents=True, exist_ok=True)
    registros = []
    for cena, segundo in AMOSTRAS:
        fonte = MIDIAS / VIDEOS[cena]
        quadro, indice, instante = extrair_quadro(fonte, segundo)
        nome = f"{cena}-{segundo:03d}s.png"
        destino = saida / nome
        if not cv2.imwrite(str(destino), quadro):
            raise ValueError(f"Não foi possível salvar {destino}.")
        registros.append(
            {
                "arquivo": nome,
                "cena": cena,
                "fonte": fonte.name,
                "quadro": indice,
                "instante_s": round(instante, 6),
                "sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
            }
        )
    manifesto = saida / "quadros.json"
    manifesto.write_text(
        json.dumps(registros, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifesto


def empacotar(manifesto, destino):
    registros = json.loads(manifesto.read_text(encoding="utf-8"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", compression=zipfile.ZIP_DEFLATED) as pacote:
        for nome in ("comparar_sam3.py", "requirements-sam3.txt"):
            pacote.write(PASTA / nome, nome)
        pacote.write(manifesto, f"quadros/{manifesto.name}")
        for registro in registros:
            nome = registro["arquivo"]
            pacote.write(manifesto.parent / nome, f"quadros/{nome}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=SAIDA)
    parser.add_argument("--zip-colab", type=Path, help="Cria um ZIP com o script e os 12 quadros.")
    args = parser.parse_args()
    manifesto = preparar(args.saida)
    print(f"{len(AMOSTRAS)} quadros preparados em {manifesto}.")
    if args.zip_colab:
        empacotar(manifesto, args.zip_colab)
        print(f"Pacote para o Colab: {args.zip_colab}.")


if __name__ == "__main__":
    main()
