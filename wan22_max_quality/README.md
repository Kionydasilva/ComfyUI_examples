# WAN 2.2 14B — workflows de qualidade máxima

Dois workflows prontos para importar no ComfyUI, montados **só com nodes nativos**.
Nenhum custom node, nenhum ComfyUI-Manager, nenhuma dependência extra — é justamente
isso que garante que o JSON importa sem erro de "missing node".

| Arquivo | O que faz |
|---|---|
| `wan22_i2v_max_quality.json` | Imagem → vídeo (image-to-video) |
| `wan22_t2v_max_quality.json` | Texto → vídeo (text-to-video) |

Saída padrão: **1280×720 nativo, 81 frames, 16 fps** (5,06 s), VP9 crf 10.

---

## 1. Downloads

Todos os arquivos vêm de um único repositório oficial:
[`Comfy-Org/Wan_2.2_ComfyUI_Repackaged`](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged).

Os nomes abaixo são os nomes reais dos arquivos no repositório e são exatamente o que
está gravado nos nodes do JSON. **Não renomeie nada**, senão o loader não encontra.

### `ComfyUI/models/diffusion_models/`

Para o workflow **i2v**:

| Arquivo | Tamanho |
|---|---|
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 14,3 GB |
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 14,3 GB |

Para o workflow **t2v**:

| Arquivo | Tamanho |
|---|---|
| `wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors` | 14,3 GB |
| `wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors` | 14,3 GB |

### `ComfyUI/models/text_encoders/`

| Arquivo | Tamanho |
|---|---|
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6,7 GB |

### `ComfyUI/models/vae/`

| Arquivo | Tamanho |
|---|---|
| `wan_2.1_vae.safetensors` | 254 MB |

> **Pegadinha que quebra muita gente:** o WAN **2.2 14B** usa a VAE do WAN **2.1**.
> O arquivo `wan2.2_vae.safetensors` existe no mesmo repositório, mas é só para o
> modelo 5B (TI2V). Se usar a VAE errada aqui, a saída vira ruído colorido.

### `ComfyUI/models/loras/` — opcional, só para o modo rápido

| Arquivo | Tamanho |
|---|---|
| `wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` | 1,2 GB |
| `wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors` | 1,2 GB |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors` | 1,2 GB |
| `wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors` | 1,2 GB |

Todos ficam em `split_files/<pasta>/<arquivo>` dentro do repositório. Exemplo de download
direto (troque o caminho conforme a tabela):

```bash
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors \
  --local-dir ./download
```

---

## 2. Por que dois modelos e dois KSamplers

O WAN 2.2 14B não é um modelo só. Ele é um MoE dividido em dois checkpoints:

- **high noise** — roda nos primeiros steps e define **movimento e composição**
- **low noise** — roda nos últimos steps e define **detalhe e textura**

Por isso o workflow tem dois `UNETLoader` e dois `KSamplerAdvanced` em série.
O primeiro sampler gera com `return_with_leftover_noise = enable` e entrega o latente
ruidoso para o segundo, que termina a denoise.

**A regra que não pode ser quebrada:** os dois KSamplers precisam ter o **mesmo `steps`**,
e o `end_at_step` do primeiro tem que ser igual ao `start_at_step` do segundo.
Se isso desalinhar, o vídeo sai borrado ou estourado — e sem mensagem de erro,
o que torna o bug difícil de achar.

---

## 3. Qualidade máxima vs. velocidade

O workflow vem configurado no **caminho de qualidade máxima**, e os dois LoRAs Lightning
vêm **em bypass** (aparecem em roxo). Isso é deliberado.

|  | Qualidade máxima (padrão) | Lightning 4 steps |
|---|---|---|
| LoRAs Lightning | bypass | ativos |
| steps | 20 (10 + 10) | 4 (2 + 2) |
| cfg | 3.5 | 1.0 |
| shift (ModelSamplingSD3) | 8.0 | 5.0 |
| tempo relativo | 1× | ~5× mais rápido |

Os LoRAs Lightning são **destilação**: eles compram velocidade pagando com amplitude de
movimento e microdetalhe. Em cena parada a diferença é pequena; em cena com movimento
grande ela é visível. Se o objetivo é qualidade máxima, o certo é deixá-los em bypass —
que é como o arquivo já vem.

### Para ativar o modo rápido

1. Selecione os dois nodes de LoRA e aperte **Ctrl+B** (tira do bypass).
2. KSampler **high noise**: `steps=4`, `cfg=1.0`, `end_at_step=2`.
3. KSampler **low noise**: `steps=4`, `cfg=1.0`, `start_at_step=2`.
4. Nos dois `ModelSamplingSD3`: `shift=5.0`.

---

## 4. VRAM

O caminho fp8 pede aproximadamente:

- **24 GB** (RTX 3090 / 4090 / 5090): roda 1280×720 / 81 frames confortável.
- **16 GB**: rode com `--lowvram`, ou baixe para 832×480 no node de resolução.
- **12 GB ou menos**: use `--lowvram`, 832×480, e considere o modelo 5B (`wan2.2_ti2v_5B`)
  em vez do 14B. Vale lembrar que o 5B usa a `wan2.2_vae.safetensors`, não a 2.1.

Só um dos dois modelos fica na VRAM por vez — o ComfyUI troca entre os passes —
mas os dois precisam caber no disco e na RAM.

Existem versões `fp16` (28,6 GB cada) no mesmo repositório. O ganho de qualidade sobre
`fp8_scaled` é marginal e o custo de VRAM é o dobro; não vale a pena fora de uma A100/H100.

---

## 5. Ajustes de duração e resolução

No node de resolução (`WanImageToVideo` no i2v, `EmptyHunyuanLatentVideo` no t2v):

- `length` precisa ser da forma **4n+1** (81, 121, 161...). 81 frames a 16 fps = 5,06 s.
- `width` e `height` precisam ser múltiplos de 16.
- 1280×720 é a resolução nativa de treino do 14B. Subir para 1920×1080 geralmente
  **piora** o resultado e explode a VRAM — o correto é gerar em 720p e fazer upscale depois.

---

## 6. Como foram validados

Os dois JSONs passaram por um validador que roda contra o `object_info` extraído de uma
instalação real do ComfyUI (mesma função `node_info()` que o backend usa), checando:

- todo tipo de node existe no `NODE_CLASS_MAPPINGS`;
- nomes e tipos de cada socket batem com o schema real do node;
- todo input obrigatório está conectado;
- integridade da tabela de links (ids únicos, slots válidos, tipos compatíveis nas duas
  pontas, referências cruzadas consistentes entre node e link);
- `order` é uma ordenação topológica válida;
- contagem de widgets igual à dos workflows oficiais do ComfyUI para o mesmo tipo de node;
- existe node de saída e ele é alcançável a partir dos loaders.

As ferramentas estão em `tools/`:

```bash
# 1. dentro de um checkout do ComfyUI, extrai os schemas reais dos nodes
python dump_object_info.py object_info.json

# 2. checagem estática do JSON contra esses schemas
python validate_workflow.py object_info.json <dir-de-referencia> workflow.json

# 3. converte para formato API e roda o validate_prompt do próprio backend
python backend_validate.py workflow.json
```

Resultado da última execução: os dois workflows deste diretório passam nas três
etapas, tanto no modo qualidade máxima (LoRAs em bypass) quanto no modo Lightning
4 steps (LoRAs ativos).
