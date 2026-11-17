import numpy as np
import pytest

from pos_processamento.avaliacao import metricas
from pos_processamento.niveis import NiveisROI, tamanho_esperado
from pos_processamento.posprocessamento import Config, escolher_config, processar
from pos_processamento.temporal import Kalman1D, suavizar_serie

ROI = NiveisROI()


def caixa(cx, cy, w=10, h=10):
    return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2]


def test_nivel_por_centro_e_descarte_fora_da_roi():
    assert ROI.nivel_de(600, 450) == "N0"
    assert ROI.nivel_de(900, 300) is None  # cortina lateral, fora de todos os níveis
    b = np.array([caixa(600, 450), caixa(900, 300)], np.float32)
    r = processar(b, np.array([0.9, 0.9]), Config(), ROI)
    assert sum(r["contagem"].values()) == 1


def test_limiar_por_nivel():
    b = np.array([caixa(600, 450), caixa(600, 455)], np.float32)
    s = np.array([0.9, 0.2])
    assert processar(b, s, Config(), ROI)["contagem"]["N0"] == 1
    cfg = Config(limiar={"N0": 0.1, "N1": 0.25, "N2": 0.25})
    assert processar(b, s, cfg, ROI)["contagem"]["N0"] == 2


def test_filtro_de_tamanho_remove_caixa_incompativel():
    w, h = tamanho_esperado(600, 450)
    b = np.array([caixa(600, 450, w, h), caixa(620, 450, w * 5, h * 5)], np.float32)
    r = processar(b, np.array([0.9, 0.9]), Config(filtro_tamanho=(0.5, 1.8)), ROI)
    assert r["contagem"]["N0"] == 1


def test_contencao_remove_duplicata():
    b = np.array([caixa(600, 450, 40, 40), caixa(600, 450, 20, 20)], np.float32)
    r = processar(b, np.array([0.9, 0.8]), Config(contencao=0.7), ROI)
    assert r["contagem"]["N0"] == 1


def test_soma_ponderada_e_fator():
    b = np.array([caixa(600, 450), caixa(600, 500)], np.float32)
    cfg = Config(soma_p=1.0, conf_piso=0.05, fator={"N0": 2.0, "N1": 1.0, "N2": 1.0})
    assert processar(b, np.array([0.5, 0.5]), cfg, ROI)["contagem"]["N0"] == pytest.approx(2.0)


def test_sem_caixas():
    r = processar(np.zeros((0, 4)), np.zeros(0), Config(), ROI)
    assert r["contagem"] == {"N0": 0.0, "N1": 0.0, "N2": 0.0}


def test_kalman_reduz_oscilacao():
    ruidosa = [100, 140, 90, 150, 95, 145, 100, 140]
    suave = suavizar_serie(ruidosa)
    assert np.abs(np.diff(suave)).mean() < np.abs(np.diff(ruidosa)).mean()
    assert Kalman1D().update(7.0) == 7.0


def test_metricas():
    m = metricas([8, 12], [10, 10])
    assert m["MAE"] == 2 and m["vies"] == 0 and m["RMSE"] == 2


def test_perfil_dia_noite():
    dia = np.zeros((576, 1024, 3), np.uint8)
    dia[:, :] = (30, 90, 200)  # cor saturada
    noite = np.full((576, 1024, 3), 90, np.uint8)  # cinza
    assert escolher_config(dia, {"N0": 0.05, "N1": 0.05, "N2": 0.4})[1] == "dia"
    assert escolher_config(noite, {"N0": 0.05, "N1": 0.05, "N2": 0.4})[1] == "noite"
