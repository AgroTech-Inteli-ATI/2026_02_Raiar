#!/usr/bin/env bash
# Primeiro boot do nó de borda Raiar: Docker + captura de câmera (v4l2), com o
# mínimo de pacotes. Execute como root no Raspberry Pi:  /root/setup_raiar_node.sh
#
# Variáveis de ambiente opcionais:
#   RAIAR_USER   usuário dos containers (padrão: alarm)
#   EXTRA_PKGS   pacotes adicionais, por exemplo "git" ou "ffmpeg" (padrão: nenhum)
#   ZRAM=1       habilita swap comprimido na RAM (zram), útil para picos de memória
#                dos modelos sem desgastar o cartão SD.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Execute como root."; exit 1; }

RAIAR_USER="${RAIAR_USER:-alarm}"
EXTRA_PKGS="${EXTRA_PKGS:-}"

# /boot precisa estar montado, ou o kernel novo seria gravado no lugar errado.
findmnt -n /boot >/dev/null || { echo "/boot não está montado (LABEL=BOOT)."; exit 1; }

# Sem RTC, o relógio começa errado e quebra TLS e assinaturas do pacman.
timedatectl set-ntp true
for _ in $(seq 1 60); do
  [[ "$(timedatectl show -p NTPSynchronized --value)" == "yes" ]] && break
  sleep 2
done

pacman-key --init && pacman-key --populate archlinuxarm

# Só o essencial: Docker, Compose e as ferramentas de câmera (v4l-utils).
# shellcheck disable=SC2086
pacman -Syu --noconfirm --needed docker docker-compose v4l-utils htop $EXTRA_PKGS
rm -rf /var/cache/pacman/pkg/*

# Limita o log dos containers para poupar disco e RAM.
install -d /etc/docker
cat > /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
JSON

systemctl enable --now docker

# Usuário dos containers: grupos docker (daemon) e video (/dev/video0).
usermod -aG docker,video "$RAIAR_USER"
install -d -o "$RAIAR_USER" -g "$RAIAR_USER" /opt/raiar

if [[ "${ZRAM:-0}" == "1" ]]; then
  pacman -S --noconfirm --needed zram-generator
  cat > /etc/systemd/zram-generator.conf <<'CONF'
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
CONF
  # Com zram, o kernel deve preferir o swap comprimido ao descarte de cache.
  echo "vm.swappiness=100" > /etc/sysctl.d/99-raiar-performance.conf
  systemctl daemon-reload
  systemctl start systemd-zram-setup@zram0.service || true
fi

echo
echo "Câmeras detectadas:"
v4l2-ctl --list-devices || true
cat <<'MSG'

Pronto. Reinicie (reboot) para carregar o kernel atualizado. Depois, exemplo de container com câmera:
  docker run --rm --device /dev/video0 --group-add $(getent group video | cut -d: -f3) <imagem>
Altere as senhas padrão de root e alarm com passwd.
MSG
