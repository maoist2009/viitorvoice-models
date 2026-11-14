#!/data/data/com.termux/files/usr/bin/bash
cd $(dirname "$(dirname "$0")") || exit 1
export HTTPS_PROXY=http://127.0.0.1:8912 HTTP_PROXY=http://127.0.0.1:8912
export SSL_CERT_FILE=/data/data/com.termux/files/usr/etc/tls/cert.pem
export HF_XET_HIGH_PERFORMANCE=1
n=0
while :; do
  n=$((n+1))
  echo "=== attempt $n $(date +%H:%M:%S) ==="
  hf upload mistmlm/viitorvoice-nar-sm8750 . . \
    --include "artifacts/*" "MANIFEST.md" "README.md" "install.sh" "verify.sh" "push_hf.sh" \
    --exclude ".git/*" --commit-message "Add SM8750 QNN model set (xet)" && { echo "=== DONE attempt $n ==="; break; }
  echo "=== attempt $n failed, retry in 20s ==="
  sleep 20
done
