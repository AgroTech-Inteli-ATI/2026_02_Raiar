"""Compara a segmentação por texto do SAM 3 nos quadros de desenvolvimento do YannET."""

import argparse
import csv
import hashlib
import json
import math
import resource
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

MODELO = "facebook/sam3"
PROMPTS = ("chicken", "chick")
MODOS = ("quadro", "recortes")
SOBREPOSICAO = 0.20


@dataclass
class Mascara:
    x: int
    y: int
    pixels: np.ndarray
    score: float
    origem: int
    cortada: bool

    @property
    def caixa(self):
        altura, largura = self.pixels.shape
        return self.x, self.y, self.x + largura, self.y + altura


def recortar(quadro, modo):
    altura, largura = quadro.shape[:2]
    if modo == "quadro":
        yield 0, 0, quadro
        return
    h = math.ceil(altura / (2 - SOBREPOSICAO))
    w = math.ceil(largura / (2 - SOBREPOSICAO))
    for y in (0, altura - h):
        for x in (0, largura - w):
            yield x, y, quadro[y : y + h, x : x + w]


def converter_mascara(pixels, score, x, y, origem, dimensoes):
    mascara = np.ascontiguousarray(pixels, dtype=np.uint8)
    u, v, largura, altura = cv2.boundingRect(mascara)
    if not largura or not altura:
        return None
    h, w = mascara.shape
    altura_total, largura_total = dimensoes
    cortada = (
        (u == 0 and x > 0)
        or (v == 0 and y > 0)
        or (u + largura == w and x + w < largura_total)
        or (v + altura == h and y + h < altura_total)
    )
    return Mascara(
        x + u, y + v, mascara[v : v + altura, u : u + largura].copy(), float(score), origem, cortada
    )


def duplicadas(a, b):
    if a.origem == b.origem:
        return False
    ax, ay, ar, af = a.caixa
    bx, by, br, bf = b.caixa
    x, y, r, f = max(ax, bx), max(ay, by), min(ar, br), min(af, bf)
    if x >= r or y >= f:
        return False
    intersecao = np.count_nonzero(
        a.pixels[y - ay : f - ay, x - ax : r - ax] & b.pixels[y - by : f - by, x - bx : r - bx]
    )
    area_a, area_b = np.count_nonzero(a.pixels), np.count_nonzero(b.pixels)
    iou = intersecao / (area_a + area_b - intersecao)
    return iou >= 0.5 or ((a.cortada or b.cortada) and intersecao / min(area_a, area_b) >= 0.8)


def segmentar(quadro, modo, prompt, prever):
    mascaras = []
    for origem, (x, y, recorte) in enumerate(recortar(quadro, modo)):
        pixels, scores = prever(cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB), prompt)
        for imagem, score in zip(pixels, scores, strict=True):
            mascara = converter_mascara(imagem, score, x, y, origem, quadro.shape[:2])
            if mascara is not None:
                mascaras.append(mascara)

    mantidas = []
    for mascara in sorted(mascaras, key=lambda m: (m.cortada, -m.score)):
        if not any(duplicadas(mascara, anterior) for anterior in mantidas):
            mantidas.append(mascara)
    return mantidas


def salvar_resultado(saida, quadro, mascaras):
    camada = quadro.copy()
    for mascara in mascaras:
        x, y, r, f = mascara.caixa
        camada[y:f, x:r][mascara.pixels != 0] = (80, 230, 90)
    previa = cv2.addWeighted(quadro, 0.55, camada, 0.45, 0)
    if not cv2.imwrite(str(saida.with_suffix(".jpg")), previa):
        raise ValueError(f"Falha ao salvar a prévia em {saida}.")
    np.savez_compressed(
        saida.with_suffix(".npz"),
        caixas_xyxy=np.asarray([m.caixa for m in mascaras], dtype=np.int32).reshape(-1, 4),
        scores=np.asarray([m.score for m in mascaras], dtype=np.float32),
        **{f"mascara_{i}": m.pixels for i, m in enumerate(mascaras)},
    )


def carregar_quadro(manifesto, registro):
    caminho = manifesto.parent / registro["arquivo"]
    conteudo = caminho.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != registro["sha256"]:
        raise ValueError(f"O quadro {caminho.name} não corresponde ao manifesto.")
    quadro = cv2.imdecode(np.frombuffer(conteudo, dtype=np.uint8), cv2.IMREAD_COLOR)
    if quadro is None:
        raise ValueError(f"Não foi possível ler {caminho}.")
    return quadro


def pico_ram_mib():
    unidade = 1024**2 if sys.platform == "darwin" else 1024
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / unidade, 1)


def executar(args):
    import torch
    from transformers import Sam3Model, Sam3Processor, __version__

    if args.dispositivo == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA indisponível. Se estiver no Colab, selecione um ambiente com GPU.")
    dispositivo = torch.device(args.dispositivo)
    torch.set_num_threads(args.threads)
    registros = json.loads(args.manifesto.read_text(encoding="utf-8"))[: args.limite]
    if not registros:
        raise ValueError("O manifesto não tem quadros de desenvolvimento.")
    if args.saida.exists():
        raise ValueError(f"A saída {args.saida} já existe. Escolha outra pasta para esta execução.")

    print(f"Carregando {MODELO} em {dispositivo}...", flush=True)
    inicio = perf_counter()
    processor = Sam3Processor.from_pretrained(MODELO)
    model = Sam3Model.from_pretrained(MODELO).to(dispositivo).eval()
    if dispositivo.type == "cuda":
        torch.cuda.synchronize(dispositivo)
    carga_s = perf_counter() - inicio

    def prever(rgb, prompt):
        inputs = processor(images=rgb, text=prompt, return_tensors="pt").to(dispositivo)
        with torch.inference_mode():
            outputs = model(**inputs)
            resultado = processor.post_process_instance_segmentation(
                outputs, threshold=0.5, mask_threshold=0.5, target_sizes=[rgb.shape[:2]]
            )[0]
        return resultado["masks"].cpu().numpy(), resultado["scores"].cpu().numpy()

    args.saida.mkdir(parents=True)
    campos = [
        "quadro",
        "cena",
        "instante_s",
        "prompt",
        "modo",
        "mascaras",
        "tempo_s",
        "pico_ram_processo_mib",
        "pico_vram_torch_mib",
        "previa",
    ]
    tempos = {}
    with (args.saida / "comparacao.csv").open("w", encoding="utf-8", newline="") as arquivo:
        csv_saida = csv.DictWriter(arquivo, fieldnames=campos)
        csv_saida.writeheader()
        for registro in registros:
            quadro = carregar_quadro(args.manifesto, registro)
            pasta = args.saida / Path(registro["arquivo"]).stem
            pasta.mkdir()
            for prompt in args.prompt:
                for modo in args.modo:
                    if dispositivo.type == "cuda":
                        torch.cuda.reset_peak_memory_stats(dispositivo)
                    inicio = perf_counter()
                    mascaras = segmentar(quadro, modo, prompt, prever)
                    tempo = perf_counter() - inicio
                    vram = (
                        round(torch.cuda.max_memory_allocated(dispositivo) / 1024**2, 1)
                        if dispositivo.type == "cuda"
                        else None
                    )
                    ram = pico_ram_mib()
                    base = pasta / f"{prompt}-{modo}"
                    salvar_resultado(base, quadro, mascaras)
                    csv_saida.writerow(
                        {
                            "quadro": registro["arquivo"],
                            "cena": registro["cena"],
                            "instante_s": registro["instante_s"],
                            "prompt": prompt,
                            "modo": modo,
                            "mascaras": len(mascaras),
                            "tempo_s": round(tempo, 3),
                            "pico_ram_processo_mib": ram,
                            "pico_vram_torch_mib": vram,
                            "previa": base.with_suffix(".jpg").relative_to(args.saida).as_posix(),
                        }
                    )
                    arquivo.flush()
                    tempos.setdefault(f"{prompt}-{modo}", []).append(tempo)
                    print(
                        f"{pasta.name} {prompt}/{modo}: {tempo:.2f} s; RAM {ram:.1f} MiB",
                        flush=True,
                    )

    resumo = {
        "modelo": MODELO,
        "revisao": getattr(model.config, "_commit_hash", None),
        "transformers": __version__,
        "torch": torch.__version__,
        "dispositivo": str(dispositivo),
        "gpu": torch.cuda.get_device_name(dispositivo) if dispositivo.type == "cuda" else None,
        "threads_cpu": args.threads,
        "limiar_deteccao": 0.5,
        "limiar_mascara": 0.5,
        "sobreposicao_recortes": SOBREPOSICAO,
        "quadros": len(registros),
        "carga_s": round(carga_s, 3),
        "mediana_segundos_por_quadro": {
            k: round(statistics.median(v), 3) for k, v in tempos.items()
        },
        "pico_ram_processo_mib": pico_ram_mib(),
    }
    (args.saida / "execucao.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Resultados em {args.saida}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--dispositivo", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--limite", type=int, help="Executa apenas os primeiros N quadros.")
    parser.add_argument("--prompt", choices=PROMPTS, action="append")
    parser.add_argument("--modo", choices=MODOS, action="append")
    args = parser.parse_args()
    if args.threads < 1 or (args.limite is not None and args.limite < 1):
        parser.error("--threads e --limite precisam ser positivos.")
    args.prompt = tuple(dict.fromkeys(args.prompt or PROMPTS))
    args.modo = tuple(dict.fromkeys(args.modo or MODOS))
    try:
        executar(args)
    except (ImportError, OSError, ValueError, RuntimeError) as erro:
        parser.exit(1, f"Experimento interrompido: {erro}\n")


if __name__ == "__main__":
    main()
