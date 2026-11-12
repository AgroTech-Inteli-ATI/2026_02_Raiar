"""Inspeciona a mídia reservada e desenha as faixas no enquadramento da câmera."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np

PASTA_MODELO = Path(__file__).resolve().parent
CONFIG = PASTA_MODELO / "cam7.json"
CORES = ((255, 185, 55), (90, 225, 140), (75, 170, 255))


def carregar_config(caminho):
    config = json.loads(caminho.read_text(encoding="utf-8"))
    if config["faixas"] != ["esquerda", "central", "direita"]:
        raise ValueError("Declare as três faixas na ordem esquerda, central e direita.")
    linhas = np.asarray(config["linhas"], dtype=float)
    if linhas.ndim != 2 or linhas.shape[1] != 5 or len(linhas) < 2:
        raise ValueError("Cada linha precisa de y e quatro limites horizontais.")
    if not np.isfinite(linhas).all() or np.any((linhas < 0) | (linhas > 1)):
        raise ValueError("As coordenadas devem estar entre 0 e 1.")
    if np.any(np.diff(linhas[:, 0]) <= 0) or np.any(np.diff(linhas[:, 1:], axis=1) <= 0):
        raise ValueError("As alturas e os limites de cada linha devem ser crescentes.")
    return config, linhas


def poligonos_faixas(dimensoes, linhas):
    altura, largura = dimensoes
    bordas = [
        np.rint(linhas[:, [i, 0]] * [largura - 1, altura - 1]).astype(np.int32) for i in range(1, 5)
    ]
    return [np.concatenate([bordas[i], bordas[i + 1][::-1]]) for i in range(3)]


def desenhar_faixas(quadro, nomes, linhas):
    poligonos = poligonos_faixas(quadro.shape[:2], linhas)
    camada = quadro.copy()
    for poligono, cor in zip(poligonos, CORES, strict=True):
        cv2.fillPoly(camada, [poligono], cor)
    previa = cv2.addWeighted(quadro, 0.80, camada, 0.20, 0)
    for poligono, cor, nome in zip(poligonos, CORES, nomes, strict=True):
        cv2.polylines(previa, [poligono], True, cor, 2, cv2.LINE_AA)
        cv2.putText(
            previa,
            nome.upper(),
            (12, 25 + 25 * nomes.index(nome)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            cor,
            2,
            cv2.LINE_AA,
        )
    return previa


def ler_video(caminho, segundo):
    captura = cv2.VideoCapture(str(caminho))
    try:
        if not captura.isOpened():
            raise ValueError(f"Não foi possível abrir o vídeo {caminho}.")
        fps = captura.get(cv2.CAP_PROP_FPS)
        total = captura.get(cv2.CAP_PROP_FRAME_COUNT)
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("O vídeo não fornece um FPS válido.")
        total = int(total) if math.isfinite(total) and total > 0 else None
        # Gravações de tela podem ter intervalos diferentes entre quadros.
        # Leia em sequência porque a busca do OpenCV pode usar o FPS médio.
        indice_lido = -1
        while True:
            ok, quadro = captura.read()
            if not ok:
                raise ValueError("Não foi possível ler um quadro no instante pedido.")
            indice_lido += 1
            instante = captura.get(cv2.CAP_PROP_POS_MSEC) / 1000
            if not math.isfinite(instante) or instante < 0:
                raise ValueError("O vídeo não fornece um timestamp válido para o quadro.")
            if instante >= segundo:
                break
        codigo = int(captura.get(cv2.CAP_PROP_FOURCC))
        codec = "".join(chr((codigo >> (8 * byte)) & 255) for byte in range(4)).rstrip("\0")
    finally:
        captura.release()

    with caminho.open("rb") as arquivo:
        sha256 = hashlib.file_digest(arquivo, "sha256").hexdigest()
    return quadro, {
        "fps": fps,
        "quadros_declarados": total,
        "duracao_estimada_s": round(total / fps, 3) if total is not None else None,
        "codec_fourcc": codec or None,
        "quadro_referencia": indice_lido,
        "instante_s": round(instante, 6),
        "sha256": sha256,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    fontes = parser.add_mutually_exclusive_group(required=True)
    fontes.add_argument("--referencia", type=Path, help="Foto de referência do enquadramento.")
    fontes.add_argument("--video", type=Path, help="Gravação original reservada para teste.")
    parser.add_argument("--segundo", type=float, help="Instante do quadro no vídeo.")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--saida", type=Path, default=PASTA_MODELO / "outputs" / "cam7")
    args = parser.parse_args()
    if args.segundo is not None:
        if not math.isfinite(args.segundo) or args.segundo < 0 or args.referencia:
            parser.error("--segundo aceita valores não negativos e se aplica somente ao vídeo.")

    caminho = args.video or args.referencia
    try:
        if not caminho.is_file():
            raise ValueError(f"Arquivo não encontrado: {caminho}.")
        config, linhas = carregar_config(args.config)
        if args.video:
            teste = config.get("video_teste", {})
            segundo = (
                args.segundo if args.segundo is not None else teste.get("quadro_referencia_s", 0)
            )
            if teste and not teste["inicio_s"] <= segundo < teste["fim_s"]:
                raise ValueError("Escolha um instante dentro do trecho reservado para a CAM 7.")
            quadro, detalhes = ler_video(caminho, segundo)
            if teste:
                altura, largura = quadro.shape[:2]
                if detalhes["sha256"] != teste["sha256"] or [largura, altura] != teste["resolucao"]:
                    raise ValueError("O vídeo não corresponde à gravação reservada no cam7.json.")
                if detalhes["instante_s"] >= teste["fim_s"]:
                    raise ValueError("O quadro lido está fora do trecho reservado.")
                detalhes["trecho_teste_s"] = [teste["inicio_s"], teste["fim_s"]]
            prefixo = "video"
        else:
            quadro = cv2.imread(str(caminho))
            if quadro is None:
                raise ValueError(f"Não foi possível ler a imagem {caminho}.")
            detalhes = {}
            prefixo = "referencia"

        altura, largura = quadro.shape[:2]
        largura_ref, altura_ref = config["resolucao_referencia"]
        relatorio = {
            "camera_declarada": config["camera"],
            "fonte": str(caminho.resolve()),
            "resolucao": [largura, altura],
            "proporcao_diferente_da_referencia": not math.isclose(
                largura / altura, largura_ref / altura_ref, rel_tol=0.01
            ),
            "configuracao": str(args.config.resolve()),
            "estado_faixas": config["estado"],
            **detalhes,
        }
        args.saida.mkdir(parents=True, exist_ok=True)
        previa = desenhar_faixas(quadro, config["faixas"], linhas)
        if args.video and not cv2.imwrite(str(args.saida / "video-quadro.png"), quadro):
            raise ValueError("Não foi possível salvar o quadro original do vídeo.")
        if not cv2.imwrite(str(args.saida / f"{prefixo}-faixas.png"), previa):
            raise ValueError("Não foi possível salvar a prévia das faixas.")
        resultado = json.dumps(relatorio, ensure_ascii=False, indent=2)
        (args.saida / f"{prefixo}.json").write_text(resultado + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError, cv2.error) as erro:
        parser.exit(1, f"Erro na preparação: {erro}\n")
    print(resultado)


if __name__ == "__main__":
    main()
