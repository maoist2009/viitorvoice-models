#!/data/data/com.termux/files/usr/bin/sh
# 校验 artifacts/ 与 MANIFEST.md 里记录的 sha256 是否一致（防止拷贝/下载损坏）。
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE/artifacts"
sed -n '/^## 完整哈希/,/^```$/p' "$HERE/MANIFEST.md" >/dev/null 2>&1 || true
# 直接从 MANIFEST 的代码块里抽 "<hash>  <file>" 行
awk '/^## 完整哈希/{f=1;next} f&&/^```/{c++} f&&c==1&&NF==3{print $1"  "$3}' "$HERE/MANIFEST.md" | sha256sum -c -
