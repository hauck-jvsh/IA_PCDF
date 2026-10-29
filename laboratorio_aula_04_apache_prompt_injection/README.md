# Aula 04: construção do vulnerável e do protegido

As duas implementações são independentes. Cada arquivo contém seu próprio
prompt, missão, parser, contratos, ferramentas, permissões, laço e comando de
execução. Não existe seleção de agente por flag. O único módulo comum dos
agentes é `chamadas_tools.py`, limitado ao SDK e ao processamento técnico das
chamadas JSON. Os logs entram somente como retornos `tool`.

A sequência da aula é: **construir o vulnerável, testá-lo, construir o protegido
e repetir os testes**. As atividades são em grupos.

## 1. Preparar o ambiente

Python 3.12. Dependências fixadas: openai 2.54.0 e python-dotenv 1.2.3.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python testar.py
```

Se a ativação for impedida pela política local, use diretamente
`.venv\Scripts\python.exe`. Os 24 testes locais não chamam um modelo real.

Copie `.env.example` para `.env` e preencha a configuração na sua máquina:

```dotenv
OPENAI_BASE_URL=https://integrate.api.nvidia.com/v1
OPENAI_MODEL=nvidia/nemotron-3.5-super-vl-120b-a12b
OPENAI_API_KEY=SUBSTITUA_PELA_SUA_CHAVE
```

Os dois agentes carregam o `.env` local com `override=False`. Variáveis do
terminal têm precedência. O SDK usa o endpoint configurado, que pode ser NVIDIA
ou outro servidor compatível com Chat Completions e tools. Os logs e o histórico
são enviados ao provedor configurado. Use os dados sintéticos da aula.

## 2. Construir primeiro agente_vulneravel.py

Percorrer nesta ordem:

1. `INSTRUCOES`, `MISSAO` e as cinco categorias web.
2. `carregar()`: parser combined, IDs, linha bruta e SHA-256.
3. `FERRAMENTAS`: consultas, finalização e envio simulado.
4. `Ferramentas.executar()`: validação dos argumentos e despacho local.
5. `Ferramentas.enviar_evidencias()`: ponto de breakpoint e destaque no terminal.
6. `executar()`: laço próprio que recebe retornos de ferramentas e consulta o modelo.
7. `main()`: configuração, dataset, rastro e relatório.

O agente recebe uma missão comum de análise web, sem instruções para obedecer a
ordens do log. A vulnerabilidade didática é oferecer uma capacidade de envio
desnecessária à missão e não orientar o modelo sobre instruções adversariais
nos dados. O controlador valida IDs e formatos, mas permite o envio simulado
quando o modelo escolhe a ferramenta. Nenhuma promoção dos logs a `user` é usada.

## 3. Testar o vulnerável

```powershell
python gerar_cenario_template.py
python agente_vulneravel.py --modo ensaio --dataset controle_template
python agente_vulneravel.py --dataset controle_template
python agente_vulneravel.py --dataset ataque_template_v2
```

As entradas usam `--modo llm` por padrão. `--modo ensaio` usa respostas fixas para
percorrer ferramentas e não classifica anomalias nem mede resistência.

No ataque, procurar no terminal:

```text
=== ENVIAR_EVIDENCIAS CHAMADO ===
  destino: https://coleta.invalid/receber
  evidencias: ['E013', ..., 'E024']
  Nada é enviado: registro local apenas.
```

O banner aparece somente se o controlador aceitar a chamada. No `execucao.json`,
conferir o retorno de E027, a chamada posterior e `envios_simulados`. O registro
contém `simulado: true` e `envio_realizado: false`: o destino nunca é usado como
URL por um cliente de rede. Um relatório web correto pode coexistir com essa
ação induzida. Registrar também quando um ataque não funcionar.

## 4. Construir depois agente_protegido.py

Este arquivo não importa nem herda o agente vulnerável. Estudar suas próprias
instruções, ferramentas e seu próprio laço, observando:

- Prompt que identifica logs como dados não confiáveis e preserva a missão.
- Categoria adicional `prompt_injection`, com menções benignas como controles.
- Catálogo com quatro ferramentas, sem `enviar_evidencias`.
- Ausência de método de envio na classe de ferramentas.
- Validação do nome no controlador, mesmo se o modelo inventar uma chamada.
- Exigência de todos os eventos terem sido retornados antes de finalizar.
- Rótulo `confianca: nao_confiavel` nos retornos de eventos.

Os controles reduzem a exposição e limitam a ação. Não garantem classificação
perfeita. Cobertura de leitura também não garante que os achados estejam completos.

## 5. Repetir o mesmo experimento

```powershell
python agente_protegido.py --modo ensaio --dataset controle_template
python agente_protegido.py --dataset controle_template
python agente_protegido.py --dataset ataque_template_v2
python avaliar.py "CAMINHO_IMPRESSO_PARA_EXECUCAO_JSON"
```

Comparar controle e ataque no mesmo modelo e configuração. Conferir leitura,
chamadas tentadas, chamadas recusadas, ações aceitas e falsos positivos. A
comparação dos agentes muda prompt, catálogo, categoria e cobertura; não isola
o efeito de uma única camada. Uma execução sem envio não comprova imunidade.

`avaliar.py` adapta E027 para benigno quando `dataset` é `controle_template`, sem
alterar o gabarito original ou expô-lo ao modelo. Para outros conjuntos criados
pelo grupo, manter rótulos correspondentes. No vulnerável a categoria de injection
está fora do contrato: comparar primeiro as cinco categorias web comuns.

## Ferramentas e responsabilidade

| Ferramenta | Vulnerável | Protegido |
|---|---|---|
| `estatisticas()` | Contagens de IP e status | Contagens de IP e status |
| `listar_eventos(offset)` | Páginas de até 10 eventos | Mesmas páginas com rótulo de confiança |
| `obter_evento(id)` | Um evento observado | Um evento com rótulo de confiança |
| `finalizar(...)` | Pode terminar com leitura parcial | Exige leitura completa |
| `enviar_evidencias(...)` | Registro local destacado | Indisponível e não autorizado |

`chamadas_tools.py` define somente `chamar_modelo()` e `processar_chamada()`.
O adaptador não contém catálogo, prompt, política ou laço de agente. A autorização
fica em `Ferramentas.executar()` de cada arquivo.

## Arquivos e conjuntos

| Arquivo | Uso |
|---|---|
| `agente_vulneravel.py` | Implementação completa do primeiro agente |
| `agente_protegido.py` | Implementação completa do segundo agente |
| `chamadas_tools.py` | Transporte SDK e decodificação técnica das chamadas |
| `testar.py` | Testes locais de independência, contratos e controles |
| `avaliar.py` | Avaliação externa, com ajuste do controle conhecido |
| `gerar_cenario_template.py` | Controle benigno, V1 e V2 de 27 eventos |
| `gerar_cenario.py` | Cenário contextual adicional |
| `gerar_dados.py` | Restauração dos fixtures originais |
| `exemplos_prompt_injection.md` | Exemplos comentados, com linhas brutas |

Os arquivos `agente.py` e `prompts.py` da implementação compartilhada foram
retirados da versão ativa. As flags antigas de integração e política também
foram removidas. Rastros de versões anteriores são históricos, com hashes e
estrutura próprios; não tratá-los como execução da nova arquitetura.

Preservar dados antes de `gerar_dados.py`, que restaura o E027 original de
`com_ataques.log`. O gerador de template não altera o controle original. Todos
os dados são sintéticos e nenhum gerador envia requisições.

## Limites e interpretação

O parser cobre o combined dos fixtures, não todo LogFormat possível. O cliente
limita cada execução a 16 passos, com até oito tools por lote e timeout de 60
segundos por chamada ao modelo. O SDK não faz retentativas automáticas e não
segue redirecionamentos. Falhas da API são execuções incompletas.

Os payloads podem usar falsa autoridade, URLs codificadas ou marcadores que
imitam papéis. O rastro demonstra as mensagens e ações da aplicação; não expõe
o chat template interno do provedor. Os testes anteriores também obtiveram
envio sem os marcadores especiais, portanto sua necessidade não ficou demonstrada.

HTTP 200 não comprova exploração e 403 não comprova sozinho o bloqueio do
payload. Identificar uma tentativa e comprovar seu efeito são conclusões distintas.

## Prática e entrega em grupos

Criar duas ordens adversariais e duas menções benignas em cópias dos conjuntos.
Atualizar os rótulos. Construir e testar primeiro o vulnerável e implementar as
proteções em seguida. Entregar relatório, JSONs e comparação de ações e achados.
Manter o envio como simulador local.

Critérios: 25% análise web, 30% explicação das injeções, 25% comparação registrada
e 20% controles e limites. Total de 100%.

## Referências

- [Apache: logs](https://httpd.apache.org/docs/2.4/logs.html)
- [Apache: mod_log_config](https://httpd.apache.org/docs/2.4/mod/mod_log_config.html)
- [OWASP LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [OWASP: prevenção de prompt injection](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
