# Face Swap em Lote (ReActor)

Workflow para trocar um rosto de referência em **várias fotos de uma vez só**, priorizando fidelidade ao rosto de referência (em vez de gerar um rosto parecido via difusão, o [ReActor](https://github.com/Gourieff/ComfyUI-ReActor) transplanta o rosto real, então o resultado fica o mais consistente possível com a imagem original).

Arquivo do workflow: [`face_swap_batch_workflow.json`](face_swap_batch_workflow.json) — carregue no ComfyUI pelo botão **Load** (ou arraste o arquivo para a janela do ComfyUI, no Chrome).

## O que o workflow faz

1. **PASSO 1** — lê uma pasta com uma ou mais fotos do rosto que você quer usar e calcula um "modelo de rosto" (média das fotos). Usar mais de uma foto de referência (ângulos/iluminação diferentes) deixa o resultado mais fiel e estável.
2. **PASSO 2** — lê uma pasta com todas as fotos-alvo (onde o rosto será colocado) e processa o lote inteiro numa única execução (Queue Prompt), aplicando o mesmo modelo de rosto em todas elas. Todas as saídas são salvas automaticamente.

Não tem problema o processo demorar — o workflow processa o lote inteiro sequencialmente, sem necessidade de clicar em nada entre uma imagem e outra.

## Nós/custom nodes necessários

Instale pelo **ComfyUI Manager** (`Manager > Custom Nodes Manager`, buscar pelo nome) ou via git clone em `ComfyUI/custom_nodes/`:

- [ComfyUI-ReActor](https://github.com/Gourieff/ComfyUI-ReActor) — faz a troca de rosto (`ReActorFaceSwap`, `ReActorBuildFaceModel`).
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) — usado aqui só para carregar todas as imagens de uma pasta como lote (`Load Images (Path)`).

Depois de instalar o ReActor, siga as instruções do próprio repositório dele para baixar os modelos necessários (o node não funciona sem eles):

- Modelo de swap: `inswapper_128.onnx`
- Detector de rosto: `retinaface_resnet50` (já vem com as dependências do ReActor)
- Restauração de rosto (deixa a pele/iluminação mais natural depois do swap): `GFPGANv1.4.pth` (ou troque por `codeformer.pth` no node se preferir)

Reinicie o ComfyUI depois de instalar os custom nodes e os modelos.

## Como usar (upload direto pelo navegador, sem mexer em pasta/servidor)

1. Carregue `face_swap_batch_workflow.json` no ComfyUI (Load, ou arraste o arquivo para a janela).
2. No node **1. Fotos de referência**, clique no botão de upload do próprio node e selecione a(s) foto(s) do rosto que você quer usar (dá pra escolher mais de uma foto de uma vez, ângulos/iluminação diferentes deixam o resultado mais fiel).
3. No node **3. Fotos-alvo**, clique no botão de upload e selecione todas as fotos onde o rosto deve ser trocado — pode selecionar o lote inteiro de uma vez.
4. Clique em **Queue Prompt**. O ComfyUI processa todas as fotos-alvo em sequência e salva os resultados em `ComfyUI/output/face_swap/`.

Você não precisa digitar caminho de pasta nem enviar nada por fora do workflow — o upload é feito pelo próprio node, direto do navegador, e os arquivos ficam guardados dentro do `ComfyUI/input/` da instância que está rodando o workflow (seja local ou num pod na nuvem).

## Ajustes finos (opcional)

- Se alguma foto tiver mais de uma pessoa, use `input_faces_index` (no node 4) para escolher qual rosto da foto-alvo será substituído (0 = primeiro rosto detectado, 1 = segundo, etc.).
- `face_restore_visibility` (0 a 1) controla o quanto da restauração de pele (GFPGAN) é aplicada — 1 = máxima naturalidade, valores menores preservam mais a textura original da foto-alvo.
- Trocar `compute_method` no node 2 para `"Median"` pode ajudar se uma das fotos de referência tiver iluminação/ângulo muito diferente das outras.
