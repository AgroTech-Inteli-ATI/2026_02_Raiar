"""Compara mapas semânticos do SAM 3 para aves e amontoamentos na foto da CAM 7."""

import argparse
import json
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from .comparar_sam3 import MODELO, pico_ram_mib
from .preparar import CONFIG, PASTA_MODELO, carregar_config, poligonos_faixas

CONCEITOS = {"aves": "chicks", "grupos": "cluster of chicks"}
ALTURAS = (0.0, 0.28, 0.50, 0.70, 1.0)
JANELAS = (0.033, 0.05, 0.08, 0.12, 0.15)
LIMIAR_EXPLORATORIO = 0.42


def salvar_focos(saida, quadro, mapa_aves, area_util):
    """Mostra regiões candidatas pela fração de pixels ocupados em uma janela local."""
    altura = quadro.shape[0]
    ocupacao = ((mapa_aves >= 0.5) & area_util).astype(np.float32)
    escala = np.interp(np.linspace(0, 1, altura), ALTURAS, np.arange(len(JANELAS)))
    concentracao = np.zeros_like(ocupacao)
    for i, tamanho_relativo in enumerate(JANELAS):
        tamanho = 2 * round(tamanho_relativo * altura / 2) + 1
        media = cv2.boxFilter(ocupacao, -1, (tamanho, tamanho), borderType=cv2.BORDER_CONSTANT)
        peso = np.maximum(0, 1 - np.abs(escala - i)).astype(np.float32)
        concentracao += media * peso[:, None]
    candidatos = (concentracao >= LIMIAR_EXPLORATORIO) & area_util
    _, rotulos, stats, centros = cv2.connectedComponentsWithStats(candidatos.astype(np.uint8))
    camada = quadro.copy()
    focos = []
    for i, (x, y, largura, h, area) in enumerate(stats[1:], 1):
        tamanho = altura * np.interp(centros[i, 1] / altura, ALTURAS, JANELAS)
        if area < 0.07 * tamanho**2:
            continue
        regiao = rotulos == i
        camada[regiao] = (80, 230, 90)
        focos.append(
            {
                "caixa_xyxy": [int(x), int(y), int(x + largura), int(y + h)],
                "ocupacao_local_maxima": round(float(concentracao[regiao].max()), 3),
            }
        )
    previa = cv2.addWeighted(quadro, 0.55, camada, 0.45, 0)
    for foco in focos:
        x1, y1, x2, y2 = foco["caixa_xyxy"]
        cv2.rectangle(previa, (x1, y1), (x2 - 1, y2 - 1), (0, 220, 255), 2, cv2.LINE_AA)
    if not cv2.imwrite(str(saida / "focos.jpg"), previa):
        raise OSError("Não foi possível salvar a prévia dos focos.")
    resultado = {"limiar_exploratorio": LIMIAR_EXPLORATORIO, "focos": focos}
    (saida / "focos.json").write_text(json.dumps(resultado, indent=2) + "\n", encoding="utf-8")


def mascara_area_util(dimensoes):
    _, linhas = carregar_config(CONFIG)
    area_util = np.zeros(dimensoes, dtype=np.uint8)
    for poligono in poligonos_faixas(dimensoes, linhas):
        cv2.fillPoly(area_util, [poligono], 1)
    return area_util.astype(bool)


def salvar_mapa(saida, nome, quadro, probabilidade, area_util):
    mascara = (probabilidade >= 0.5) & area_util
    camada = quadro.copy()
    camada[mascara] = (80, 230, 90)
    previa = cv2.addWeighted(quadro, 0.55, camada, 0.45, 0)
    if not cv2.imwrite(str(saida / f"{nome}.jpg"), previa):
        raise OSError(f"Não foi possível salvar a prévia de {nome}.")
    np.save(saida / f"{nome}.npy", np.where(area_util, probabilidade, 0))
    return int(mascara.sum())


def executar(foto, saida, dispositivo):
    import torch
    from torch.nn.functional import interpolate
    from transformers import Sam3Model, Sam3Processor

    quadro = cv2.imread(str(foto))
    if quadro is None:
        raise ValueError(f"Não foi possível ler {foto}.")
    if saida.exists():
        raise ValueError(f"Escolha uma pasta de saída nova. {saida} já existe.")
    if dispositivo == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA indisponível.")

    dimensoes = quadro.shape[:2]
    area_util = mascara_area_util(dimensoes)
    torch.set_num_threads(4)
    cache = PASTA_MODELO / "outputs" / "cache-hf"
    processor = Sam3Processor.from_pretrained(MODELO, cache_dir=cache)
    modelo = Sam3Model.from_pretrained(MODELO, cache_dir=cache).to(dispositivo).eval()
    inputs = processor(images=cv2.cvtColor(quadro, cv2.COLOR_BGR2RGB), return_tensors="pt")
    saida.mkdir(parents=True)
    resumo = {"fonte": foto.name, "modelo": MODELO, "dispositivo": dispositivo, "mapas": {}}
    with torch.inference_mode():
        inicio = perf_counter()
        print("Processando a foto da CAM 7...", flush=True)
        imagem = modelo.get_vision_features(pixel_values=inputs.pixel_values.to(dispositivo))
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        resumo["tempo_imagem_s"] = round(perf_counter() - inicio, 3)
        for nome, texto in CONCEITOS.items():
            inicio = perf_counter()
            texto_inputs = processor(text=texto, return_tensors="pt").to(dispositivo)
            resultado = modelo(vision_embeds=imagem, **texto_inputs)
            logits = interpolate(
                resultado.semantic_seg, size=dimensoes, mode="bilinear", align_corners=False
            )
            mapa = logits[0, 0].sigmoid().float().cpu().numpy()
            tempo = round(perf_counter() - inicio, 3)
            pixels = salvar_mapa(saida, nome, quadro, mapa, area_util)
            resumo["mapas"][nome] = {"texto": texto, "tempo_s": tempo, "pixels_ativos": pixels}
            if nome == "aves":
                salvar_focos(saida, quadro, mapa, area_util)
            print(f"{texto}: {tempo:.3f} s; mapa salvo em {saida / (nome + '.jpg')}", flush=True)
    resumo["pico_ram_mib"] = pico_ram_mib()
    (saida / "execucao.json").write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foto", type=Path, default=PASTA_MODELO / "referencia-cam7.png")
    parser.add_argument("--saida", type=Path, default=PASTA_MODELO / "outputs" / "cam7-foto-piloto")
    parser.add_argument("--dispositivo", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    try:
        executar(args.foto, args.saida, args.dispositivo)
    except (ImportError, OSError, ValueError, RuntimeError) as erro:
        parser.exit(1, f"Experimento interrompido: {erro}\n")


if __name__ == "__main__":
    main()
