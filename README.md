---
license: apache-2.0
library_name: qnn
tags:
  - qnn
  - qualcomm
  - snapdragon
  - hexagon-npu
  - text-to-speech
  - voice-cloning
  - on-device
language:
  - zh
  - en
base_model:
  - Qwen/Qwen3-0.6B
---

# ViiTorVoice-NAR → Qualcomm Hexagon NPU (SM8750)

QNN context binaries (`.bin`) for running the ViiTorVoice-NAR text-to-speech / voice-cloning
chain entirely on a Snapdragon 8 Elite (SM8750) Hexagon NPU: **w2v-BERT semantic encoder →
dualcodec encode-core → 32-step masked-diffusion NAR → dualcodec decoder**.

Compiled with QAIRT 2.51 / qai-hub (`onnx → dlc → qairt-dlc-prepare → .bin`), tested on
Android 16 with a `com.viitorvoice.demo` app that loads these through `QnnContext_createFromBinary`.

## Files

| group | files | notes |
|---|---|---|
| semantic frontend | `enc_fe.bin` (1.50 GB), `fe_mel.bin` | w2v-BERT, **fp16** single context, chunked 32×6k frames at inference |
| encode-core | `enc_e1..e3`, `enc_front`, `enc_e4b`, `enc_e5`, `enc_e6` (104 MB total) | 7 linked segments; `enc_front` runs 32× per encode |
| NAR backbone | `llm.bin` (894 MB), `head.bin` (57 MB) | Qwen3-0.6B, multi-shape **shared weight** link (weights stored once) |
| embeddings | `text_emb.bin`, `sem_emb.bin`, `aco_emb.bin` (165 MB) | text embedding table + 12 codebook embeddings, gathered on CPU |
| decoder | `dec_p1..p5.bin` (138 MB) | 5-graph chain; **p1 must stay fp16**, p2–p4 w8a16, p5 uses `chunk=48` |
| config | `nar_steps` | NAR diffusion steps, `32` |

Hub: <https://huggingface.co/mistmlm/viitorvoice-nar-sm8750> (private) — `push_hf.sh` syncs this dir.

See `MANIFEST.md` for sizes + sha256, `install.sh` to copy the set into an Android app's
private dir (`/data/data/<pkg>/files/models`) with correct owner/SELinux label.

## Uploading off phone without burning VPN quota

The phone routes everything through a TUN proxy, but the proxy has a traffic quota and
the model set is ~2.85 GB. `net/` solves it with a local CONNECT proxy that splits planes:

* `huggingface.co` (SNI-blocked, a few KB of API calls) → default route / VPN
* everything else (`*.hf.co`, `*.xethub.hf.co`, `*.amazonaws.com`) → `SO_BINDTODEVICE wlan0`
  with a real direct IP (UDP DNS to 223.5.5.5, never the fake-ip system resolver)

```sh
sudo python3 net/pinproxy.py &          # needs root for SO_BINDTODEVICE
net/upload_loop.sh                      # xet upload with retry (hf has no built-in retry)
```

Measured on 2026-11-14: 2.85 GB at 1.4–3.6 MB/s, **0.1 MB total through the VPN**.
See `verify.sh` (local sha256) and the API check in the playbook memory for post-upload validation.

## Precision policy

* No fp32 anywhere in a compiled graph — QNN rejects it.
* Weights w8a16 (int8 weight / int16 activation) except the two places where it degrades
  quality audibly: the w2v frontend and decoder segment 1, both fp16.
* Post-training quantization is done offline (QDQ export + folding weight-side Q with numpy),
  not via compile-time PTQ — the latter trips a `PostLayout::addTensor` bug on these graphs.

## Usage

Everything runs offline on device; no HF access needed at runtime:

```sh
./install.sh com.viitorvoice.demo      # copies into the app's private dir (needs root)
```

The app calls `QnnContext_createFromBinary` once per file and chains them with its own
`vv_encode / vv_nar / vv_pipeline` C++ code.

## Provenance

* Source models: [ViiTorVoice](https://github.com/ViiTor/ViiTor-Voice) (Apache-2.0),
  Qwen3-0.6B backbone (Apache-2.0), dualcodec.
* Pipeline scripts: `~/projects/viitorvoice/pipeline` (qai-hub submit + link + download).
* Derived artifacts only; upstream weights are not redistributed here beyond what the
  QNN contexts embed.
