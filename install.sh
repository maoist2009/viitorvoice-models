#!/data/data/com.termux/files/usr/bin/sh
# 把 models/artifacts 装进 demo app 的私有目录（需要 KSU sudo）。
#   ./install.sh                 # 目标 com.viitorvoice.demo.tmp
#   ./install.sh com.viitorvoice.demo
set -eu
PKG=${1:-com.viitorvoice.demo.tmp}
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/artifacts
DST=/data/data/$PKG/files/models

[ -d "/data/data/$PKG" ] || { echo "没装 $PKG" >&2; exit 1; }
U=$(sudo stat -c %u "/data/data/$PKG")
G=$(sudo stat -c %g "/data/data/$PKG")

echo "-> $DST  ($U:$G)"
sudo mkdir -p "$DST"
sudo cp -f "$SRC"/*.bin "$DST/"
sudo cp -f "$SRC/nar_steps" "$DST/"
sudo chown -R "$U:$G" "$DST"
sudo chmod 600 "$DST"/*.bin
sudo chmod 644 "$DST"/nar_steps
sudo restorecon -R "/data/data/$PKG/files" 2>/dev/null || true
echo "完成：$(sudo ls "$DST" | wc -l) 项"
