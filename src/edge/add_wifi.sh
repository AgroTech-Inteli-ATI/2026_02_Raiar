#!/usr/bin/env bash
# Adiciona (ou atualiza) uma rede Wi-Fi no nó de borda, sem apagar as anteriores.
# O nó tenta as redes conhecidas e entra na de maior prioridade que estiver ao alcance.
#
# Uso, no Raspberry Pi, como root:
#   /root/add_wifi.sh "NOME_DA_REDE" "SENHA" [prioridade]
#   /root/add_wifi.sh --list
#
# Prioridade: número inteiro; maior é preferida (padrão: 5). A rede de fábrica do
# provisionamento fica com prioridade 0. A senha é gravada já derivada (PSK em hex).
# Para redes abertas ou corporativas (WPA-EAP), edite o arquivo à mão.
set -euo pipefail

CONF="/etc/wpa_supplicant/wpa_supplicant-wlan0.conf"
die() { printf '\033[1;31m[raiar-edge] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "execute como root."
[[ -f "$CONF" ]] || die "$CONF não existe; o Wi-Fi não foi provisionado neste nó."

if [[ "${1:-}" == "--list" ]]; then
  grep -E '^\s*(ssid|priority)=' "$CONF"
  exit 0
fi

SSID="${1:-}"; PSK="${2:-}"; PRIO="${3:-5}"
[[ -n "$SSID" && -n "$PSK" ]] || die 'uso: add_wifi.sh "SSID" "SENHA" [prioridade]'
(( ${#PSK} >= 8 && ${#PSK} <= 63 )) || die "a senha WPA precisa ter de 8 a 63 caracteres."
[[ "$PRIO" =~ ^[0-9]+$ ]] || die "prioridade deve ser um número inteiro."

# Remove o bloco anterior da mesma rede, se houver, e grava a cópia de segurança.
cp -a "$CONF" "$CONF.bak"
TMP="$(mktemp)"
awk -v target="ssid=\"$SSID\"" '
  /^network=\{/ { inblk = 1; buf = $0 "\n"; hit = 0; next }
  inblk {
    buf = buf $0 "\n"
    s = $0; sub(/^[ \t]*/, "", s)
    if (s == target) hit = 1
    if ($0 ~ /^\}/) { inblk = 0; if (!hit) printf "%s", buf }
    next
  }
  { print }
' "$CONF" > "$TMP"
cat "$TMP" > "$CONF"; rm -f "$TMP"

{
  echo
  wpa_passphrase "$SSID" "$PSK" | grep -v '^\s*#psk=' | sed "s/^}/\tpriority=$PRIO\n}/"
} >> "$CONF"
chmod 600 "$CONF"

# Aplica sem reiniciar. A conexão pode cair por alguns segundos ao trocar de rede.
if command -v wpa_cli >/dev/null && wpa_cli -i wlan0 reconfigure >/dev/null 2>&1; then
  echo "Rede '$SSID' adicionada (prioridade $PRIO) e aplicada."
else
  systemctl restart wpa_supplicant@wlan0.service
  echo "Rede '$SSID' adicionada (prioridade $PRIO); serviço reiniciado."
fi
