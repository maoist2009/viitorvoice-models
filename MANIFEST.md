# ViiTorVoice 端侧模型清单（artifacts/）

运行 `com.viitorvoice.demo` 所需的全部 QNN context binary。**合计 2.7 GB / 20 项**，与设备上
`/data/data/<pkg>/files/models/` 一一对应，`install.sh` 负责装回去。

这些 `.bin` 由 qai-hub 编译（ONNX → DLC → `qairt-dlc-prepare`）得到，脚本见
`../pipeline/qaihub/`；`.bin` 是 **prepare 之后**的产物，`.dlc` 在端侧无法加载。

## 编码器

| 文件 | 字节 | sha256 | 说明 |
|---|---:|---|---|
| `enc_fe.bin` | 1496645632 | `0dc7150d…1c90f0` | w2v-BERT 语义前端，fp16，整图一个 context，推理时按 32×6k 帧分块 |
| `fe_mel.bin` | 83840 | `45562275…bd6306` | log-mel 前端（5.4 ms/次） |
| `enc_e1.bin` | 20930560 | `d05a832f…6d0e2` | encode-core 第 1 段（fp16，VTCM 敏感） |
| `enc_e2.bin` | 20066304 | `b753de6e…1321a` | encode-core 第 2 段 |
| `enc_e3.bin` | 14508032 | `a92bf3a7…6df1e` | encode-core 第 3 段 |
| `enc_front.bin` | 2396160 | `3bd0b18f…4bab` | 分块前端（推理时 ×32） |
| `enc_e4b.bin` | 7921664 | `2d248ded…88fba` | encode-core 第 4 段 |
| `enc_e5.bin` | 30461952 | `d0977c22…fe4fb` | encode-core 第 5 段 |
| `enc_e6.bin` | 7798784 | `320c734c…07ecc3` | encode-core 第 6 段（码本输出，12×200） |

## NAR 主干

| 文件 | 字节 | sha256 | 说明 |
|---|---:|---|---|
| `llm.bin` | 893554688 | `cb6fd5cf…b60d3` | Qwen3-0.6B backbone，多 shape 共享权重的 **link** 产物 |
| `head.bin` | 57413632 | `347611aa…4e796` | NAR 输出头（32 步 masked diffusion 用） |
| `text_emb.bin` | 107923456 | `dbabc52f…6ab2e` | 文本 embedding 表（CPU 侧 gather） |
| `sem_emb.bin` | 33560576 | `0f8b27c8…ebd3c6` | 语义码本嵌入 |
| `aco_emb.bin` | 23136256 | `dd48dab5…c0ba0` | 声学码本嵌入 |
| `nar_steps` | 10 | — | NAR 迭代步数，现为 `32`（8/16 步实验过，音质不足已回退） |

## 解码器（dualcodec，5 段链）

| 文件 | 字节 | sha256 | 说明 |
|---|---:|---|---|
| `dec_p1.bin` | 88330240 | `3ae086c2…03a85` | 第 1 段，**必须 fp16**（w8a16 会崩） |
| `dec_p2.bin` | 19922944 | `68e3eb44…7eda9` | 第 2 段，w8a16（a16 变体） |
| `dec_p3.bin` | 6393856 | `25dfd687…52fe` | 第 3 段，w8a16 |
| `dec_p4.bin` | 16887808 | `f37d1f10…06367` | 第 4 段，w8a16 |
| `dec_p5.bin` | 6135808 | `e670d88d…e47dca` | 第 5 段，`chunk=48`，与解码长度无关 |

## 完整哈希

```
dd48dab59e1302255f6e1d7d4185c41fb1b3bab81ca0c9ddf6cfc6fe5cdc0ba0   23136256  aco_emb.bin
3ae086c24ea962173c541fa153bef4fa3664da7c2defe6b995e59256b4403a85   88330240  dec_p1.bin
68e3eb44a9a426144f314f495cbc3972dd8a7e926ad3e7d97e984bddba47eda9   19922944  dec_p2.bin
25dfd6874074b932206aaedeae47cfc518b6d64526e8cac1a6e9d839eab852fe    6393856  dec_p3.bin
f37d1f1088b6a189b29ed251c182075047fe2b98e8fd62fc45acaa1cb6106367   16887808  dec_p4.bin
e670d88d43718ab02c13ba39f228d410da16c9df11b490f511eab457e7e47dca    6135808  dec_p5.bin
d05a832f59588e0c5524de25f5b4066047a67316e0db26209ef5d1fc3f86d0e2   20930560  enc_e1.bin
b753de6e0cea1e20d60a3cf950b9488d4439057dba4a8bf3b0ce77b15d81321a   20066304  enc_e2.bin
a92bf3a73561cf995bd3e61f733351bf353283c1106c8c432ea0aff83cc6df1e   14508032  enc_e3.bin
2d248dedadc702236b9c7e12ba05ccef0d611014f250818074136c2363888fba    7921664  enc_e4b.bin
d0977c223f3dbaff2a88ff50c934ee6d545379259eab33ef53ef26ccb38fe4fb   30461952  enc_e5.bin
320c734cae17669ca422da2673d083a15e5496b0fd295aa80da68b355807ecc3    7798784  enc_e6.bin
0dc7150d71da93c7ea1258672be96d833b41b47022aa76e326bf9554371c90f0 1496645632  enc_fe.bin
3bd0b18fd2cdc4a22cf420d1aa9169a26b7bbdd7ed45ba622dd0b893045e4bab    2396160  enc_front.bin
45562275cc93de20f72b44dfeace2803f32864d92db282e5d930bc875bbd6306      83840  fe_mel.bin
347611aa3637ea85b4803dcb9cef1e19d244c5875a791c77bfb7bdd70fa4e796   57413632  head.bin
cb6fd5cf2fc103ff7cc12c9f4af313f4b8a3be66a4b0731e219d5a0ad35b60d3  893554688  llm.bin
0f8b27c8332ce1a01f3684b9f5860bda7fe42bd4cd114a34a5138825a5ebd3c6   33560576  sem_emb.bin
dbabc52ffd24f2db2aa1571ba230bace06991cf1c3e8bed1f1ed56c1c296ab2e  107923456  text_emb.bin
```

`sha256sum -c` 用的格式就是上面四列去掉前两列（`<hash>  <file>`）。

## 注意

* 这些文件**不进 git**（见 `.gitignore`）：没有 git-lfs，二进制进 `.git` 等于再占一份空间。
  备份/分发靠 `artifacts/` 目录本身（或后续推到 HF / 外置存储）。
* 设备上的副本是 `install.sh` 拷进 app 私有目录的**第三份**；调试时允许直接删 app 数据，
  重装用 `install.sh` 即可（2026-11-14 就是这么恢复的）。
* 源模型（ONNX 权重、dualcodec ckpt、Qwen3 backbone）在
  `~/projects/voice_editor/sm8750_voice_editor/viitor-voice-nar/local_models/`（11 GB），
  不属于本仓库；重新编译时从这里出发。
