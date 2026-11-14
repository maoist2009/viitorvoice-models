#!/data/data/com.termux/files/usr/bin/sh
# 把 models/ 同步到 HuggingFace（默认 mistmlm/viitorvoice-nar-sm8750，private）。
#
# xet 在 Termux 会 panic（rustls-platform-verifier 走 JNI，没有 JVM）：
#   "Expect rustls-platform-verifier to be initialized"
# 给它一个 CA bundle 就退回文件校验路径，xet 恢复正常：
export SSL_CERT_FILE=/data/data/com.termux/files/usr/etc/tls/cert.pem
export HF_XET_HIGH_PERFORMANCE=1
set -eu
REPO=${1:-mistmlm/viitorvoice-nar-sm8750}
cd "$(dirname "$0")"
hf upload "$REPO" . . \
  --include "artifacts/*" "MANIFEST.md" "README.md" "install.sh" "verify.sh" "push_hf.sh" \
  --exclude ".git/*" \
  --commit-message "sync SM8750 QNN model set"
