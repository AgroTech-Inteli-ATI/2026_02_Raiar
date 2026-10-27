#!/usr/bin/env bash
# Enxuga o Arch Linux ARM de um nó de borda (Raspberry Pi 4) para liberar
# armazenamento e RAM para os containers dos modelos. Funciona offline: só remove.
#
# Uso, no Raspberry Pi, como root:
#   /root/slim_arch_rpi4.sh            # mostra o que vai sair e pede confirmação
#   /root/slim_arch_rpi4.sh --yes      # sem perguntar
#
# Variáveis de ambiente:
#   KEEP_REALTEK=1   mantém o firmware Realtek (use se tiver adaptador USB Realtek).
#
# O que remove (nada disso é usado por um nó headless com Wi-Fi/Ethernet nativos):
#   - firmware de GPUs e placas Wi-Fi/Ethernet de PCs (~900 MB); fica só o da Broadcom
#     (Wi-Fi do Pi) e o do Raspberry Pi;
#   - vim (o nano continua), netctl, dialog, dhcpcd e wireless_tools (a rede usa
#     systemd-networkd e wpa_supplicant);
#   - manuais, documentação e traduções (fica pt_BR), hoje e em futuras instalações.
# Nunca faz git push.

set -euo pipefail

log()  { printf '\033[1;34m[raiar-edge]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[raiar-edge] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "execute como root."
ASSUME_YES=0
[[ "${1:-}" == "--yes" ]] && ASSUME_YES=1

installed() { pacman -Qq "$1" >/dev/null 2>&1; }

used_mb() { df -m --output=used / | tail -n1 | tr -d ' '; }
BEFORE="$(used_mb)"

# ----------------------------------------------------------- 1. firmware
# O meta-pacote linux-firmware depende de todos os subpacotes. Marcamos como
# explícitos os que queremos manter e removemos o meta com suas dependências.
KEEP_FW=(linux-firmware-broadcom firmware-raspberrypi)
[[ "${KEEP_REALTEK:-0}" == "1" ]] && KEEP_FW+=(linux-firmware-realtek)

REMOVE=()
if installed linux-firmware; then
  for p in "${KEEP_FW[@]}"; do installed "$p" && pacman -D --asexplicit "$p" >/dev/null; done
  REMOVE+=(linux-firmware)
fi

# ----------------------------------------------------- 2. programas dispensáveis
for p in ex-vi-compat vim vim-runtime netctl dialog dhcpcd wireless_tools; do
  installed "$p" && REMOVE+=("$p")
done

if ((${#REMOVE[@]})); then
  log "Pacotes que serão removidos (com dependências que ninguém mais usa):"
  pacman -Rs --print --print-format '%s %n' "${REMOVE[@]}" \
    | sort -nr | awk '{ printf "  %7.1f MB  %s\n", $1/1e6, $2; t += $1 } END { printf "  Total: %.0f MB\n", t/1e6 }'
  if ((ASSUME_YES == 0)); then
    read -r -p "Remover? (digite SIM): " ans
    [[ "$ans" == "SIM" ]] || die "cancelado."
  fi
  pacman -Rns --noconfirm "${REMOVE[@]}"
else
  log "Nenhum pacote para remover."
fi

# ------------------------------------------- 3. documentação e traduções
log "Impedindo manuais, docs e traduções nas próximas instalações (pacman.conf)..."
NOEXTRACT='NoExtract = usr/share/man/* usr/share/doc/* usr/share/info/* usr/share/locale/* !usr/share/locale/pt_BR/* !usr/share/locale/locale.alias'
if ! grep -q '^NoExtract = usr/share/man' /etc/pacman.conf; then
  sed -i "/^\[options\]/a $NOEXTRACT" /etc/pacman.conf
fi

log "Apagando manuais, docs e traduções já instalados (mantém pt_BR)..."
rm -rf /usr/share/man/* /usr/share/doc/* /usr/share/info/*
find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name pt_BR ! -name locale.alias -exec rm -rf {} +

# ------------------------------------------------------------- 4. caches
log "Limpando o cache do pacman..."
rm -rf /var/cache/pacman/pkg/*
journalctl --vacuum-size=1M >/dev/null 2>&1 || true

# ------------------------------------------------ 5. serviço que só atrasa o boot
# Com Wi-Fi, systemd-networkd-wait-online pode segurar o boot por até 2 minutos.
systemctl disable systemd-networkd-wait-online.service >/dev/null 2>&1 || true

sync
AFTER="$(used_mb)"
log "Disco usado: ${BEFORE} MB -> ${AFTER} MB (liberou $((BEFORE - AFTER)) MB)."
log "Memória após o boot (referência):"
free -m
