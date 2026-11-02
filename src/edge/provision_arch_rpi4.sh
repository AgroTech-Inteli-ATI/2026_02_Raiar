#!/usr/bin/env bash
# Provisiona um cartão SD com Arch Linux ARM aarch64 ultra-leve para os nós de
# borda (Edge Computing) do aviário: Raspberry Pi 4 Model B, headless, com todo o
# armazenamento no cartão SD e o máximo de RAM livre para os containers de
# identificação e contagem de aves.
#
# Uso (como root, a partir do notebook de desenvolvimento):
#   sudo src/edge/provision_arch_rpi4.sh /dev/mmcblk0   # leitor de cartão interno
#   sudo src/edge/provision_arch_rpi4.sh /dev/sdX       # leitor USB
#   sudo src/edge/provision_arch_rpi4.sh /dev/sdX --yes-erase=/dev/sdX   # sem pergunta
#
# Variáveis de ambiente opcionais:
#   WIFI_SSID / WIFI_PSK  Rede Wi-Fi do nó. Se omitidas, usa a conexão Wi-Fi ativa
#                         do notebook (NetworkManager). A senha fica só no cartão SD.
#   NODE_HOSTNAME         Nome do nó (padrão: raiar-edge-01).
#   CACHE_DIR             Onde guardar o tarball baixado (padrão: ~/.cache/raiar-edge).
#   TARBALL               Caminho de um tarball já baixado (pula o download).
#   MIRROR                Origem do tarball (padrão: os.archlinuxarm.org/os).
#
# ATENÇÃO: apaga TODO o conteúdo do dispositivo informado. Nunca faz git push.

set -euo pipefail

TARBALL_NAME="ArchLinuxARM-rpi-aarch64-latest.tar.gz"
MIRROR="${MIRROR:-http://os.archlinuxarm.org/os}"
NODE_HOSTNAME="${NODE_HOSTNAME:-raiar-edge-01}"
BOOT_MNT="/tmp/rpi_boot"
ROOT_MNT="/tmp/rpi_root"

log()  { printf '\033[1;34m[raiar-edge]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[raiar-edge] AVISO:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[raiar-edge] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- argumentos
DEVICE=""
CONFIRM_FLAG=""
for arg in "$@"; do
  case "$arg" in
    --yes-erase=*) CONFIRM_FLAG="${arg#--yes-erase=}" ;;
    -h|--help)     sed -n '2,20p' "$0"; exit 0 ;;
    /dev/*)        DEVICE="$arg" ;;
    *)             die "argumento desconhecido: $arg" ;;
  esac
done
[[ -n "$DEVICE" ]] || die "informe o dispositivo, por exemplo: $0 /dev/sdX"
[[ $EUID -eq 0 ]] || die "execute como root (sudo)."

for cmd in lsblk parted wipefs mkfs.vfat mkfs.ext4 bsdtar curl md5sum partprobe wpa_passphrase; do
  command -v "$cmd" >/dev/null || die "comando ausente: $cmd"
done

# ------------------------------------------------- proteção do disco do host
# 1. Tem de ser um disco inteiro (não partição): um cartão SD no leitor interno
#    (mmcblk*, que costuma constar como não removível) ou um disco removível em USB
#    (leitor de cartão externo).
[[ -b "$DEVICE" ]] || die "$DEVICE não é um dispositivo de bloco."
[[ "$(lsblk -dno TYPE "$DEVICE")" == "disk" ]] || die "$DEVICE não é um disco inteiro."
DEV_NAME="$(basename "$DEVICE")"
REMOVABLE="$(cat "/sys/block/$DEV_NAME/removable" 2>/dev/null || echo 0)"
TRAN="$(lsblk -dno TRAN "$DEVICE" | tr -d ' ')"
if [[ "$DEV_NAME" != mmcblk* ]]; then
  [[ "$REMOVABLE" == "1" ]] || die "$DEVICE não é removível (RM=0). Recusado."
  [[ "$TRAN" == "usb" ]]    || die "$DEVICE não está em barramento USB (TRAN=$TRAN). Recusado."
fi
# Nunca o disco que sustenta o sistema em execução.
HOST_SRC="$(findmnt -no SOURCE / || true)"
HOST_DISK="$(lsblk -no PKNAME "$HOST_SRC" 2>/dev/null | head -n1 || true)"
[[ -z "$HOST_DISK" || "/dev/$HOST_DISK" != "$DEVICE" ]] || die "$DEVICE é o disco do sistema do notebook. Recusado."

# 2. Nenhuma parte dele pode sustentar /, /home, /boot ou /var do notebook.
while read -r mp; do
  case "$mp" in
    /|/home|/boot|/boot/efi|/var|/var/*|/usr|/etc)
      die "$DEVICE contém o ponto de montagem do host: $mp. Recusado." ;;
  esac
done < <(lsblk -nro MOUNTPOINTS "$DEVICE" | tr ' ' '\n' | sed '/^$/d')

# 3. Tamanho mínimo plausível (o tarball descompactado ocupa ~2 GiB).
SIZE_BYTES="$(lsblk -bdno SIZE "$DEVICE")"
(( SIZE_BYTES >= 4*1024*1024*1024 )) || die "$DEVICE tem menos de 4 GiB."

log "Dispositivo alvo detectado:"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS,RM,MODEL,TRAN "$DEVICE"

# 4. Dupla validação: o operador precisa digitar o caminho exato do dispositivo.
if [[ "$CONFIRM_FLAG" == "$DEVICE" ]]; then
  log "Confirmação recebida por --yes-erase=$DEVICE."
else
  warn "TODO o conteúdo de $DEVICE será apagado."
  read -r -p "Digite o caminho do dispositivo para confirmar ($DEVICE): " ans1
  [[ "$ans1" == "$DEVICE" ]] || die "confirmação incorreta."
  read -r -p "Segunda validação: digite APAGAR para continuar: " ans2
  [[ "$ans2" == "APAGAR" ]] || die "confirmação incorreta."
fi

# ------------------------------------------------------------------- limpeza
cleanup() {
  set +e
  sync
  mountpoint -q "$BOOT_MNT" && umount "$BOOT_MNT"
  mountpoint -q "$ROOT_MNT" && umount "$ROOT_MNT"
}
trap cleanup EXIT

part() { # nome da partição N (sda1, mmcblk0p1, nvme0n1p1...)
  if [[ "$DEVICE" =~ [0-9]$ ]]; then echo "${DEVICE}p$1"; else echo "${DEVICE}$1"; fi
}

# ---------------------------------------------------------------- download
CACHE_DIR="${CACHE_DIR:-${SUDO_USER:+$(getent passwd "$SUDO_USER" | cut -d: -f6)}/.cache/raiar-edge}"
[[ "$CACHE_DIR" == /.cache/* ]] && CACHE_DIR="/root/.cache/raiar-edge"
mkdir -p "$CACHE_DIR"
TARBALL="${TARBALL:-$CACHE_DIR/$TARBALL_NAME}"

if [[ ! -f "$TARBALL" || ! -f "$TARBALL.md5" ]]; then
  log "Baixando $TARBALL_NAME (≈850 MB)..."
  curl -fL -C - --retry 5 -o "$TARBALL" "$MIRROR/$TARBALL_NAME"
  curl -fL --retry 5 -o "$TARBALL.md5" "$MIRROR/$TARBALL_NAME.md5"
fi
log "Verificando integridade (md5)..."
EXPECTED="$(cut -d' ' -f1 "$TARBALL.md5")"
ACTUAL="$(md5sum "$TARBALL" | cut -d' ' -f1)"
[[ "$EXPECTED" == "$ACTUAL" ]] || die "md5 diverge; apague $TARBALL e rode de novo."

# ----------------------------------------------- Wi-Fi do notebook (se existir)
WIFI_SSID="${WIFI_SSID:-}"
WIFI_PSK="${WIFI_PSK:-}"
if [[ -z "$WIFI_SSID" ]] && command -v nmcli >/dev/null; then
  CON="$(nmcli -t -f NAME,TYPE con show --active | awk -F: '$2=="802-11-wireless"{print $1; exit}')"
  if [[ -n "$CON" ]]; then
    WIFI_SSID="$(nmcli -g 802-11-wireless.ssid con show "$CON")"
    WIFI_PSK="$(nmcli -s -g 802-11-wireless-security.psk con show "$CON")"
  fi
fi
if [[ -z "$WIFI_SSID" || -z "$WIFI_PSK" ]]; then
  warn "Wi-Fi não configurado (defina WIFI_SSID e WIFI_PSK). O nó precisará de cabo Ethernet."
fi

# ------------------------------------------ 1. particionamento e formatação
log "Desmontando partições de $DEVICE..."
for p in $(lsblk -nro PATH "$DEVICE" | tail -n +2); do
  if findmnt -rn -S "$p" >/dev/null; then
    umount "$p" || die "não consegui desmontar $p. Feche janelas do gerenciador de arquivos que mostrem o cartão e tente de novo (veja: fuser -vm \$(findmnt -rn -o TARGET -S $p))."
  fi
done

log "Limpando assinaturas e criando tabela msdos..."
wipefs -a "$DEVICE"
parted -s "$DEVICE" mklabel msdos
parted -s "$DEVICE" mkpart primary fat32 1MiB 513MiB
parted -s "$DEVICE" set 1 boot on
parted -s "$DEVICE" mkpart primary ext4 513MiB 100%
partprobe "$DEVICE"; sleep 2

log "Formatando BOOT (FAT32) e ROOT (ext4)..."
mkfs.vfat -F 32 -n BOOT "$(part 1)"
mkfs.ext4 -F -L ROOT "$(part 2)"

# ------------------------------------------------ 2. extração do Arch Linux ARM
mkdir -p "$BOOT_MNT" "$ROOT_MNT"
mount "$(part 2)" "$ROOT_MNT"
mount "$(part 1)" "$BOOT_MNT"

log "Extraindo o sistema (bsdtar)..."
bsdtar -xpf "$TARBALL" -C "$ROOT_MNT"
sync
mv "$ROOT_MNT"/boot/* "$BOOT_MNT"/
sync

# ------------------------------------------ 3. adaptação do boot (cartão SD)
# O tarball rpi-aarch64 usa o U-Boot como kernel8.img e não tem cmdline.txt:
# os argumentos do kernel vêm do boot.scr (compilado de boot.txt), que já usa
# "root=PARTUUID=<partição 2 do dispositivo de boot> rw rootwait". Assim o sistema
# monta a raiz no mesmo dispositivo de onde o kernel foi carregado: o cartão SD.
# Mantemos essa linha, porque trocar por root=LABEL=ROOT exigiria recompilar o
# boot.scr com mkimage (pacote uboot-tools). Só validamos que o rootwait existe.
log "Adaptando fstab e verificando o boot por PARTUUID..."
grep -q 'rootwait' "$BOOT_MNT/boot.txt" || die "boot.txt sem rootwait; revise o tarball."
grep -q 'PARTUUID' "$BOOT_MNT/boot.txt" || die "boot.txt sem root=PARTUUID; revise o tarball."
[[ ! -f "$BOOT_MNT/cmdline.txt" ]] || sed -i -E 's#root=[^ ]+#root=LABEL=ROOT#; /rootwait/! s#$# rootwait#' "$BOOT_MNT/cmdline.txt"

cat > "$ROOT_MNT/etc/fstab" <<'EOF'
# Static information about the filesystems.
# See fstab(5) for details.

# <file system> <dir> <type> <options> <dump> <pass>
LABEL=ROOT  /      ext4  defaults,noatime  0  1
LABEL=BOOT  /boot  vfat  defaults,noatime  0  0
EOF

# ---------------------------------------- 4. otimização extrema de memória RAM
log "Aplicando otimizações de RAM (headless)..."
cat >> "$BOOT_MNT/config.txt" <<'EOF'

# --- Raiar Orgânicos: nó de borda headless com o máximo de RAM livre ---
gpu_mem=16
dtoverlay=disable-bt
dtparam=audio=off
EOF

# Com o U-Boot o kernel carrega o dtb de /dtbs e ignora os overlays do config.txt;
# por isso bloqueamos também os módulos de Bluetooth e áudio no próprio kernel.
cat > "$ROOT_MNT/etc/modprobe.d/raiar-lowram.conf" <<'EOF'
blacklist hci_uart
blacklist btbcm
blacklist bluetooth
blacklist snd_bcm2835
blacklist snd_soc_hdmi_codec
EOF

sed -i -E '/^#?SystemMaxUse=/d; /^#?Storage=/d; /^#?RuntimeMaxUse=/d' "$ROOT_MNT/etc/systemd/journald.conf"
cat >> "$ROOT_MNT/etc/systemd/journald.conf" <<'EOF'
Storage=volatile
SystemMaxUse=30M
RuntimeMaxUse=30M
EOF

cat > "$ROOT_MNT/etc/sysctl.d/99-raiar-performance.conf" <<'EOF'
vm.swappiness=10
EOF

echo "$NODE_HOSTNAME" > "$ROOT_MNT/etc/hostname"

# ------------------------------------------------------ 5. Wi-Fi pré-configurado
if [[ -n "$WIFI_SSID" && -n "$WIFI_PSK" ]]; then
  log "Pré-configurando Wi-Fi '$WIFI_SSID' (wpa_supplicant + systemd-networkd)..."
  install -d -m 755 "$ROOT_MNT/etc/wpa_supplicant"
  {
    printf 'ctrl_interface=/run/wpa_supplicant\nupdate_config=0\ncountry=BR\n'
    # wpa_passphrase grava o PSK já derivado (hex); descartamos a linha em texto puro.
    wpa_passphrase "$WIFI_SSID" "$WIFI_PSK" | grep -v '^\s*#psk='
  } > "$ROOT_MNT/etc/wpa_supplicant/wpa_supplicant-wlan0.conf"
  chmod 600 "$ROOT_MNT/etc/wpa_supplicant/wpa_supplicant-wlan0.conf"

  cat > "$ROOT_MNT/etc/systemd/network/wlan.network" <<'EOF'
[Match]
Name=wl*

[Network]
DHCP=yes
DNSSEC=no

[DHCPv4]
RouteMetric=600
EOF
  ln -sf /usr/lib/systemd/system/wpa_supplicant@.service \
    "$ROOT_MNT/etc/systemd/system/multi-user.target.wants/wpa_supplicant@wlan0.service"
fi
# sshd, systemd-networkd, systemd-resolved e timesyncd já vêm habilitados no tarball.

# Chave pública SSH (opcional): permite entrar no nó headless sem digitar senha.
SSH_PUBKEY_FILE="${SSH_PUBKEY_FILE:-}"
if [[ -z "$SSH_PUBKEY_FILE" && -n "${SUDO_USER:-}" ]]; then
  HOME_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)"
  for k in id_ed25519.pub id_rsa.pub; do
    [[ -f "$HOME_DIR/.ssh/$k" ]] && { SSH_PUBKEY_FILE="$HOME_DIR/.ssh/$k"; break; }
  done
fi
if [[ -n "$SSH_PUBKEY_FILE" && -f "$SSH_PUBKEY_FILE" ]]; then
  log "Instalando chave SSH pública de $SSH_PUBKEY_FILE para o usuário alarm."
  install -d -m 700 -o 1000 -g 1000 "$ROOT_MNT/home/alarm/.ssh"
  install -m 600 -o 1000 -g 1000 "$SSH_PUBKEY_FILE" "$ROOT_MNT/home/alarm/.ssh/authorized_keys"
fi

# ------------------------------------------- scripts de borda (primeiro boot)
log "Instalando os scripts de borda em /root..."
EDGE_DIR="$(dirname "$(readlink -f "$0")")"
install -m 755 "$EDGE_DIR/setup_raiar_node.sh" "$ROOT_MNT/root/setup_raiar_node.sh"
install -m 755 "$EDGE_DIR/slim_arch_rpi4.sh" "$ROOT_MNT/root/slim_arch_rpi4.sh"

# Clonador para o cartão SD. Só serve ao caminho alternativo de quem não tem leitor
# de cartão: nele, este script grava um pen drive de partida e o clonador copia o
# sistema dele para o SD. Com o SD gravado direto, não é necessário.
install -m 755 "$EDGE_DIR/clone_to_sd.sh" "$ROOT_MNT/root/clone_to_sd.sh"

# ------------------------------------------------------------------- final
log "Sincronizando e desmontando..."
sync
umount "$BOOT_MNT" "$ROOT_MNT"
trap - EXIT
log "Pronto! Coloque o cartão SD no Raspberry Pi 4 e ligue."
log "Acesso: ssh alarm@$NODE_HOSTNAME (senha padrão: alarm). No nó, como root (senha padrão: root), rode: /root/setup_raiar_node.sh"
