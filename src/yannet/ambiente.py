"""Verifica a máquina e o acesso aos pesos do SAM 3 sem baixar o modelo."""

import argparse
import json
import sys

MODELO = "facebook/sam3"


def verificar_dispositivo(dispositivo):
    try:
        import torch

        cuda_disponivel = torch.cuda.is_available()
        if dispositivo == "cuda" and not cuda_disponivel:
            return {"disponivel": False, "erro": "CUDA indisponível no PyTorch"}
        torch.ones(1, device=dispositivo).item()
        return {
            "torch": torch.__version__,
            "cuda_do_torch": torch.version.cuda,
            "disponivel": True,
            "gpu": torch.cuda.get_device_name(0) if dispositivo == "cuda" else None,
        }
    except (ImportError, OSError, RuntimeError) as erro:
        return {"disponivel": False, "erro": str(erro)}


def verificar_transformers():
    try:
        from transformers import Sam3Model, Sam3Processor, __version__

        return {"versao": __version__, "classes": [Sam3Model.__name__, Sam3Processor.__name__]}
    except (ImportError, OSError, RuntimeError) as erro:
        return {"erro": str(erro)}


def verificar_acesso():
    try:
        from huggingface_hub import HfApi, get_token
        from huggingface_hub.errors import GatedRepoError
    except ImportError:
        return "instale huggingface-hub para verificar o acesso"

    try:
        if not get_token():
            return "sem sessão autenticada no Hugging Face"
        HfApi().auth_check(MODELO, repo_type="model", token=True)
    except GatedRepoError:
        return "conta sem acesso aos pesos restritos"
    except Exception as erro:
        return f"acesso não confirmado ({type(erro).__name__})"
    return "confirmado"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dispositivo", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument(
        "--verificar-acesso", action="store_true", help="Consulta o Hub usando a sessão local."
    )
    args = parser.parse_args()
    dispositivo = verificar_dispositivo(args.dispositivo)
    transformers = verificar_transformers()
    acesso = verificar_acesso() if args.verificar_acesso else "não consultado"
    python_ok = sys.version_info >= (3, 12)
    ambiente_ok = python_ok and dispositivo["disponivel"] and "erro" not in transformers
    print(
        json.dumps(
            {
                "modelo": MODELO,
                "python": sys.version.split()[0],
                "python_3_12_ou_superior": python_ok,
                "dispositivo": {"tipo": args.dispositivo, **dispositivo},
                "transformers": transformers,
                "acesso_pesos": acesso,
                "ambiente_ok": ambiente_ok,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ambiente_ok and (not args.verificar_acesso or acesso == "confirmado") else 1


if __name__ == "__main__":
    raise SystemExit(main())
