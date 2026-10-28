#!/usr/bin/env bash
# CAMINHO ALTERNATIVO, só para quem NÃO tem leitor de cartão no notebook. O destino
# final do nó é sempre o cartão SD; o pen drive é só o veículo de partida.
# Clona o sistema que está rodando no Raspberry Pi 4 (iniciado por um Pen Drive USB
# provisionado) para o cartão SD, mantendo o layout do provision_arch_rpi4.sh:
# BOOT (FAT32, 512 MiB) e ROOT (ext4).
#
# Uso, no Raspberry Pi, como root:
#   1. Ligue o Pi com o Pen Drive e SEM o cartão SD (se o SD tiver um sistema, o Pi
#      daria boot por ele). Com o Pi ligado, encaixe o cartão no slot.
#   2. /root/clone_to_sd.sh            # alvo padrão: /dev/mmcblk0
#      /root/clone_to_sd.sh /dev/mmcblk0 --yes-erase=/dev/mmcblk0
#   3. Desligue (poweroff), tire o Pen Drive e ligue: o Pi inicia pelo SD.
#
# O boot usa root=PARTUUID da partição 2 do dispositivo de boot (U-Boot) e o fstab
# usa LABEL=BOOT; por isso nada precisa ser reescrito na cópia. Deixe só um
# dispositivo com os rótulos BOOT/ROOT conectado ao iniciar. Nunca faz git push.

set -euo pipefail

BOOT_MNT="/tmp/sd_boot"
ROOT_MNT="/tmp/sd_root"

log()  { printf '\033[1;34m[raiar-edge]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[raiar-edge] AVISO:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[raiar-edge] ERRO:\033[0m %s\n' "$*" >&2; exit 1; }

TARGET="/dev/mmcblk0"
CONFIRM_FLAG=""
for arg in "$@"; do
  case "$arg" in
    --yes-erase=*) CONFIRM_FLAG="${arg#--yes-erase=}" ;;
    -h|--help)     sed -n '2,17p' "$0"; exit 0 ;;
    /dev/*)        TARGET="$arg" ;;
    *)             die "argumento desconhecido: $arg" ;;
  esac
done
[[ $EUID -eq 0 ]] || die "execute como root."
for cmd in lsblk parted wipefs mkfs.vfat mkfs.ext4 tar partprobe findmnt; do
  command -v "$cmd" >/dev/null || die "comando ausente: $cmd. Instale com: pacman-key --init && pacman-key --populate archlinuxarm && pacman -Syu parted dosfstools (e reinicie)."
done

# ------------------------------------------------------------ proteção do disco
[[ -b "$TARGET" ]] || die "$TARGET não existe. O cartão está encaixado? (lsblk)"
[[ "$(lsblk -dno TYPE "$TARGET")" == "disk" ]] || die "$TARGET não é um disco inteiro."

# O alvo nunca pode ser o disco que sustenta o sistema em execução.
ROOT_SRC="$(findmnt -no SOURCE /)"
ROOT_DISK="/dev/$(lsblk -no PKNAME "$ROOT_SRC" | head -n1)"
[[ "$TARGET" != "$ROOT_DISK" ]] || die "$TARGET é o disco do sistema em execução ($ROOT_DISK). Recusado."
if lsblk -nro MOUNTPOINTS "$TARGET" | grep -qE '^(/|/boot)$'; then
  die "$TARGET contém / ou /boot em uso. Recusado."
fi
SIZE_BYTES="$(lsblk -bdno SIZE "$TARGET")"
(( SIZE_BYTES >= 4*1024*1024*1024 )) || die "$TARGET tem menos de 4 GiB."

log "Origem (em execução): $ROOT_SRC (disco $ROOT_DISK)"
log "Destino a ser APAGADO:"
lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS,RM,MODEL,TRAN "$TARGET"

if [[ "$CONFIRM_FLAG" == "$TARGET" ]]; then
  log "Confirmação recebida por --yes-erase=$TARGET."
else
  warn "TODO o conteúdo de $TARGET será apagado."
  read -r -p "Digite o caminho do dispositivo para confirmar ($TARGET): " ans1
  [[ "$ans1" == "$TARGET" ]] || die "confirmação incorreta."
  read -r -p "Segunda validação: digite APAGAR para continuar: " ans2
  [[ "$ans2" == "APAGAR" ]] || die "confirmação incorreta."
fi

cleanup() {
  set +e
  sync
  mountpoint -q "$BOOT_MNT" && umount "$BOOT_MNT"
  mountpoint -q "$ROOT_MNT" && umount "$ROOT_MNT"
}
trap cleanup EXIT

part() { # mmcblk0 -> mmcblk0p1; sdb -> sdb1
  if [[ "$TARGET" =~ [0-9]$ ]]; then echo "${TARGET}p$1"; else echo "${TARGET}$1"; fi
}

# ---------------------------------------------------- particionamento e formatação
for p in $(lsblk -nro PATH "$TARGET" | tail -n +2); do
  if findmnt -rn -S "$p" >/dev/null; then
    umount "$p" || die "não consegui desmontar $p."
  fi
done

log "Criando tabela msdos e partições..."
wipefs -a "$TARGET"
parted -s "$TARGET" mklabel msdos
parted -s "$TARGET" mkpart primary fat32 1MiB 513MiB
parted -s "$TARGET" set 1 boot on
parted -s "$TARGET" mkpart primary ext4 513MiB 100%
partprobe "$TARGET"; sleep 2

log "Formatando BOOT e ROOT..."
mkfs.vfat -F 32 -n BOOT "$(part 1)"
mkfs.ext4 -F -L ROOT "$(part 2)"

mkdir -p "$BOOT_MNT" "$ROOT_MNT"
mount "$(part 2)" "$ROOT_MNT"
mount "$(part 1)" "$BOOT_MNT"

# ------------------------------------------------------------------------ cópia
# /boot é outro ponto de montagem (vfat), então o tar de / com --one-file-system
# não o inclui; ele é copiado à parte. Pseudo-sistemas (/proc, /sys, /dev, /run)
# também ficam de fora e entram como diretórios vazios.
log "Copiando /boot..."
cp -a /boot/. "$BOOT_MNT"/
log "Copiando o sistema raiz (pode levar alguns minutos)..."
tar --one-file-system --numeric-owner --xattrs --acls -cpf - -C / . \
  | tar --numeric-owner --xattrs --acls -xpf - -C "$ROOT_MNT"

log "Sincronizando e desmontando..."
sync
umount "$BOOT_MNT" "$ROOT_MNT"
trap - EXIT
log "Pronto! Rode 'poweroff', tire o Pen Drive e ligue o Pi: ele iniciará pelo SD."
