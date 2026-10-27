# Aula 02: agentes na engenharia reversa de malware

Missão aberta: analisar o malware Android aberto no JADX, explicar seu funcionamento em alto nível, investigar elementos ofuscados ou potencialmente maliciosos e extrair IOCs sustentados por evidências. O material não contém perguntas-guia, respostas esperadas nem análise da amostra.

## Equipe e fluxo

O orquestrador invoca os especialistas como ferramentas pelo OpenAI Agents SDK. O hunt escolhe buscas a partir da estrutura e do código encontrados. O analista reabre as evidências, explica o funcionamento e extrai os IOCs. O relator recebe o dossiê consolidado e redige o resumo. O orquestrador pode solicitar novas rodadas antes do relatório.

Os quatro agentes são instâncias de `Agent`. Cada delegação executa um novo `Runner` no mesmo programa Python. Os resultados retornam ao orquestrador. O exemplo não exige processos ou máquinas separados para os agentes. O servidor MCP e o JADX continuam sendo processos locais separados.

## Pré-requisitos

- JADX 1.5.6 aberto com uma cópia da amostra de malware do curso.
- Plugin `jadx-ai-mcp-6.5.0.jar` instalado e respondendo na porta 8650.
- Servidor `jadx-mcp-server-6.5.0.zip` iniciado em Streamable HTTP, `http://127.0.0.1:8651/mcp`.
- Python 3.12 e backend compatível com Chat Completions, tools e saídas estruturadas JSON Schema; ou API pública OpenAI com chave e modelo compatíveis.

A configuração do JADX e do servidor está na aula 01. Esta aula usa outro ambiente virtual, porque o SDK de agentes usa versões diferentes das dependências do chat anterior.

## Instalação

Extraia este pacote em `C:\lab_jadx\agentes`.

```powershell
Set-Location 'C:\lab_jadx\agentes'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

O arquivo fixa OpenAI Agents SDK 0.24.0, OpenAI SDK 3.35.1, MCP 1.28.1, httpx 0.28.1, Pydantic 2.14.1, cryptography 50.0.2 e json-repair 0.64.1. As dependências transitivas podem variar. Não instale essas versões sobre o ambiente da aula 01.

## Execução

Mantenha o JADX e o servidor MCP ativos. A equipe usa Chat Completions, com o mesmo destino configurável do chat da aula 01. No terminal da equipe, defina as variáveis e execute diretamente o Python do venv:

```powershell
$segredo = Read-Host 'Chave da API' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $segredo).Password
Remove-Variable segredo
$env:OPENAI_BASE_URL = 'http://127.0.0.1:9931/v1'
$env:OPENAI_MODEL = 'unsloth/GLM-4.7-Flash-GGUF:UD-Q4_K_XL'
$env:JADX_MCP_URL = 'http://127.0.0.1:8651/mcp'
$env:AMOSTRA_SHA256 = (Get-FileHash -Algorithm SHA256 'C:\lab_jadx\amostras\amostra_malware.apk').Hash.ToLower()
.\.venv\Scripts\python.exe equipe_malware.py
```

| Variável | Configuração |
|---|---|
| `OPENAI_API_KEY` | Obrigatória para o SDK; chave válida na API pública, ou valor aceito pelo backend local |
| `OPENAI_BASE_URL` | Padrão `http://127.0.0.1:9931/v1`; API pública `https://api.openai.com/v1` |
| `OPENAI_MODEL` | Identificador disponível no destino; o exemplo usa `unsloth/GLM-4.7-Flash-GGUF:UD-Q4_K_XL` |
| `JADX_MCP_URL` | `http://127.0.0.1:8651/mcp` |
| `AMOSTRA_SHA256` | Hash de 64 caracteres do APK aberto no JADX |

Para usar a API pública, substitua `OPENAI_BASE_URL` por `https://api.openai.com/v1`, use uma chave válida do projeto e um modelo compatível, como `gpt-4.1-mini` quando disponível na conta.

Sem `OPENAI_MODEL`, o código usa `gpt-4.1-mini`. Esse fallback não instala nem disponibiliza o modelo em um servidor local. Confira o identificador em `GET /v1/models` e o suporte a function calling e saídas estruturadas JSON Schema. A equipe mantém `output_type` e schemas de ferramentas; um backend que só aceite texto ou ferramentas simples pode rejeitar o pedido. O SDK também envia `parallel_tool_calls=False`, `store=False` e o limite de tokens. Confira a compatibilidade desses parâmetros. Não há conversão automática para respostas sem contrato.

Confira manualmente que o APK aberto no JADX é o mesmo arquivo cujo hash foi informado. O script valida o formato do hash e o registra, mas não comprova sozinho essa correspondência. Ele não abre nem executa o APK. O `.env.example` documenta as variáveis e não é carregado automaticamente. A execução ensinada usa as variáveis da sessão do PowerShell.

A missão fica em `prompts.py`. Execute com essa missão aberta. Não acrescente uma lista de respostas que espera encontrar. As tarefas de aprofundamento devem surgir dos próprios achados.

## Arquivos do programa

| Arquivo | Função |
|---|---|
| `equipe_malware.py` | Orquestração, MCP auditado, validações e exportação |
| `prompts.py` | Missão geral e instruções dos quatro agentes |
| `contratos.py` | Saídas estruturadas das etapas |
| `transformacoes.py` | Operações determinísticas e limitadas sobre bytes |
| `modelo_relatorio.md` | Estrutura para revisão pelo investigador |

## Controles implementados

O hunt e o analista recebem uma lista de ferramentas de leitura do JADX. O orquestrador recebe apenas as ferramentas que invocam os especialistas. O relator não recebe MCP nem ferramentas de cálculo. As funções de disponibilidade impedem análise antes do hunt e relatório antes da análise da versão mais recente das pistas.

O dossiê entra nas instruções dos especialistas por código. Não depende apenas de o orquestrador copiar corretamente os dados. Pistas, achados e IOCs usam IDs. Todas as pistas precisam constar da análise, inclusive como descartadas ou pendentes. O relator precisa referenciar todos os IDs não descartados da análise. A exportação monta a parte técnica a partir dos registros estruturados, preservando os estados.

Em `main`, `AsyncOpenAI(base_url=BASE_URL)` abre o cliente e `OpenAIProvider(openai_client=api, use_responses=False)` configura o provedor. O mesmo `CONFIG` chega ao Runner externo e às três ferramentas `as_tool`, mantendo os quatro agentes em Chat Completions. O cliente permanece aberto durante a missão e fecha ao encerrar. O código não envia opções exclusivas da Responses API.

Cada consulta MCP recebe um ID `M...` e cada transformação bem-sucedida recebe um ID `T...`. As evidências precisam citar uma fonte existente e um trecho literal contido no retorno registrado. Quando a consulta inclui `class_name`, o programa confere também o nome da classe. Isso não prova que a interpretação do código esteja correta, que o trecho seja suficiente ou que o IOC seja malicioso. A revisão do investigador continua necessária.

O código limita a execução a 60 chamadas MCP, oito receitas de transformação, seis delegações concluídas, 14 turnos externos e 20 minutos. Cada especialista também tem seu limite de turnos. Limites de turnos e chamadas não são um teto de gastos. Falhas e novas tentativas podem consumir chamadas adicionais de modelo até o limite externo. As receitas aceitam até 12 passos, com limite de 64 KiB, e retornos longos ao modelo são marcados como truncados.

## Transformações sobre bytes

O analista pode chamar `reproduzir_transformacao`, citando os registros de onde vieram as entradas. A receita é um JSON com `entrada_hex` e uma lista `passos`. O programa aceita somente as operações implementadas: decodificação Base64 ou hexadecimal, hashes, PBKDF2-HMAC, XOR, decifragem AES-CBC, remoção de preenchimento PKCS7 e recorte de bytes. Os parâmetros ficam na descrição da ferramenta e no código.

Essa capacidade não direciona a investigação para uma rotina particular. O analista só deve usá-la quando a lógica encontrada justificar a operação e os parâmetros. A ferramenta não executa Python gerado, não importa componentes do APK e não acessa arquivos nem rede. Rotinas não suportadas viram lacunas no relatório. O programa confere que os registros de origem existem, mas a equivalência entre a receita e o código original exige revisão humana.

## Resultados

Cada execução cria `resultados\<data_hora>\` com:

- `metadados.json`: hash informado, missão, modelo e limites.
- `fontes.json`: consultas, retornos, receitas e resultados locais.
- `eventos.jsonl`: ordem das consultas, transformações e etapas concluídas.
- `hunt.json`: rodadas de triagem.
- `analise.json`: explicação de funcionamento, achados, IOCs e cobertura.
- `relatorio_agente.json`: saída estruturada do relator.
- `relatorio.md`: rascunho para revisão, com evidências e limitações.
- `iocs.csv`: indicadores e candidatos não descartados, com estados e fontes.

O relatório não promove candidatos a indicadores comprovados. `sustentado_no_codigo` significa associação sustentada por análise estática, sem afirmar comunicação ativa ou comprometimento de outro sistema. Valores de bibliotecas e serviços compartilhados exigem contexto. Uma chave, rotina ou constante interna pode ser um artefato analítico sem ser um IOC útil para detecção.

Se o programa parar antes do relator, os arquivos parciais permanecem disponíveis e a execução não é apresentada como concluída. Reduza o escopo, revise o erro ou prepare uma nova execução. Não troque o projeto do JADX enquanto os agentes estiverem trabalhando.

## Revisão da entrega

O investigador confere identidade da amostra, trechos no JADX, cadeia de chamadas, transformações reproduzidas, papel de cada IOC e partes não examinadas. A leitura em alto nível deve explicar gatilhos, fluxos de dados, transformações e efeitos sustentados pelas evidências. Não infira execução ou atribuição apenas pelo código.

O tracing remoto do SDK fica desativado no exemplo. Isso não impede o envio de código e resultados para o destino configurado em `OPENAI_BASE_URL`. Confira se o backend local processa tudo localmente ou encaminha requisições; na API pública, valem as políticas da conta. Os registros locais contêm material da análise e devem permanecer no ambiente do curso. Para encerrar, feche o programa, encerre o servidor quando terminar o laboratório e remova a chave do ambiente:

```powershell
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
```

## Fontes

Se a execução falhar, confira as variáveis no mesmo terminal e o executável do venv. Um erro `No Python at ...` indica que o ambiente aponta para uma instalação removida: recrie-o com o Python disponível e reinstale os requisitos. Erros de `response_format`/`json_schema` exigem conferir o suporte do backend aos contratos. Os arquivos parciais continuam disponíveis quando uma etapa falha.

- [SDK de agentes](https://developers.openai.com/api/docs/guides/agents/sdk)
- [Modelos e provedores](https://developers.openai.com/api/docs/guides/agents/models)
- [Orquestração e especialistas como ferramentas](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [Ferramentas e agents-as-tools](https://developers.openai.com/api/docs/guides/tools)
- [Integrações MCP e observabilidade](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [Servidor JADX MCP](https://github.com/zinja-coder/jadx-mcp-server)
- [MITRE ATT&CK para Android](https://attack.mitre.org/matrices/mobile/android/)


## Alternativa com a mesma equipe no OpenCode

A pasta `opencode/` contém a configuração, os quatro agentes, a ponte de transformações e o passo a passo em `opencode/README.md`. Extraia o pacote completo para manter as dependências nos caminhos indicados.
