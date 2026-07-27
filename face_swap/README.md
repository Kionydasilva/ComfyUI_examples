# Face Swap (ReActor)

Workflows para trocar um rosto de referência em fotos-alvo, priorizando fidelidade ao rosto de referência (em vez de gerar um rosto parecido via difusão, o [ReActor](https://github.com/Gourieff/ComfyUI-ReActor) transplanta o rosto real, então o resultado fica o mais consistente possível com a imagem original).

Tem dois arquivos de workflow neste repo — **comece pelo simples**:

## 1. [`face_swap_workflow_simples.json`](face_swap_workflow_simples.json) — comece por aqui

Usa só nodes nativos do ComfyUI (`LoadImage`/`SaveImage`) + o ReActor. Sem nenhuma outra dependência de upload, então é a opção mais confiável se o upload em lote não estiver funcionando para você.

- 1 node de upload para o **rosto de referência**.
- 4 pares de node de upload (**foto-alvo**) → **ReActor** → **resultado**, todos usando o mesmo rosto de referência.
- Cada `Load Image` tem seu próprio botão nativo de upload (o mesmo botão que qualquer workflow de ComfyUI usa) — clique nele e escolha o arquivo do seu computador.
- Precisa de mais de 4 fotos-alvo? Selecione o grupo "Foto-alvo N + ReActor N + Resultado N", copie (Ctrl+C/Ctrl+V) e ligue a saída do node "0. Rosto de referência" na entrada `source_image` do ReActor novo.
- Clique em **Queue Prompt** — todas as trocas configuradas rodam de uma vez.

## 2. [`face_swap_workflow_avancado_lote.json`](face_swap_workflow_avancado_lote.json) — lote maior, precisa de um custom node extra

Mesma ideia, mas usa `ComfyUI-VideoHelperSuite` para permitir selecionar **várias fotos de uma vez só** em um único botão de upload (em vez de um node por foto), e monta um modelo de rosto com a média de várias fotos de referência.

- **PASSO 1** — lê as fotos do rosto de referência que você envia e calcula um "modelo de rosto" (média das fotos). Mais de uma foto de referência (ângulos/iluminação diferentes) deixa o resultado mais fiel.
- **PASSO 2** — recebe todas as fotos-alvo enviadas de uma vez e processa o lote inteiro numa única execução (Queue Prompt).

Se esse node aparecer vermelho/quebrado ao carregar o workflow, é sinal que o `ComfyUI-VideoHelperSuite` não está instalado — use o workflow simples (opção 1) enquanto isso, ou instale o pacote e recarregue.

Não tem problema o processo demorar — nenhum dos dois workflows precisa de clique manual entre uma imagem e outra depois que você aperta Queue Prompt.

## Custom nodes necessários

Instale pelo **ComfyUI Manager** (`Manager > Custom Nodes Manager`, buscar pelo nome) ou via git clone em `ComfyUI/custom_nodes/`:

- [ComfyUI-ReActor](https://github.com/Gourieff/ComfyUI-ReActor) — faz a troca de rosto (`ReActorFaceSwap`, `ReActorBuildFaceModel`). **Necessário para os dois workflows.**
- [ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) — necessário **só** para o workflow avançado (upload de várias imagens de uma vez).

Depois de instalar o ReActor, siga as instruções do próprio repositório dele para baixar os modelos necessários (o node não funciona sem eles):

- Modelo de swap: `inswapper_128.onnx`
- Detector de rosto: `retinaface_resnet50` (já vem com as dependências do ReActor)
- Restauração de rosto (deixa a pele/iluminação mais natural depois do swap): `GFPGANv1.4.pth` (ou troque por `codeformer.pth` no node se preferir)

Reinicie o ComfyUI depois de instalar os custom nodes e os modelos.

## Se o upload não funcionar em nenhum dos dois

Isso não é mais um problema do workflow em si — é algo no ambiente do ComfyUI. Verifique:

1. Abra o **console do navegador** (F12 → aba Console) ao clicar em upload e veja se aparece algum erro em vermelho.
2. Confirme que a pasta `ComfyUI/input/` existe e tem permissão de escrita (o upload salva o arquivo ali).
3. Confirme a versão do ComfyUI (`Manager > Update ComfyUI`, ou olhe o rodapé da interface) — versões muito antigas às vezes têm bugs no upload.
4. Teste o upload num workflow **em branco**, com um `Load Image` novo (arraste do menu de nodes) — se nem isso funcionar, o problema é geral do ComfyUI/navegador, não deste workflow específico.

## Ajustes finos (opcional)

- Se alguma foto tiver mais de uma pessoa, use `input_faces_index` (no node ReActor) para escolher qual rosto da foto-alvo será substituído (0 = primeiro rosto detectado, 1 = segundo, etc.).
- `face_restore_visibility` (0 a 1) controla o quanto da restauração de pele (GFPGAN) é aplicada — 1 = máxima naturalidade, valores menores preservam mais a textura original da foto-alvo.
- No workflow avançado, trocar `compute_method` (node 2) para `"Median"` pode ajudar se uma das fotos de referência tiver iluminação/ângulo muito diferente das outras.
