# A mesma equipe no OpenCode

Esta rota mantém orquestrador, hunt, analista e relator e usa o mesmo projeto JADX.
Ela reproduz os papéis, mas não instala os callbacks e validadores do programa Python.
As regras de sequência e versão são instruções ao modelo nesta configuração.

## Preparação e versão

Extraia o pacote completo em `C:\lab_jadx\agentes`. Esta pasta `opencode` deve ser
irmã de `.venv` e de `transformacoes.py`. Instale os requisitos do pacote no venv
para usar a ponte de cálculo. O OpenCode em si não depende do OpenAI Agents SDK.

Use OpenCode no Windows, já instalado e no PATH. Confira `opencode --version` e
guarde a versão com a entrega. A configuração foi conferida com OpenCode 1.18.29.
Documentação consultada em 21/10/2026. Reconfira a sintaxe ao trocar de versão.
Não há instalação automática de OpenCode, do modelo ou do servidor MCP neste pacote.

Antes de iniciar, instale a biblioteca usada pela ferramenta local. Este passo
requer Node.js com npm. O arquivo `.opencode/package.json` fixa
`@opencode-ai/plugin` em `1.19.0`, correspondente à versão do OpenCode usada
na correção. Preserve também o `package-lock.json` incluído no pacote.

```powershell
Set-Location 'C:\lab_jadx\agentes\opencode'
npm ci --prefix .opencode --ignore-scripts --no-audit --no-fund
opencode --version
opencode agent list
opencode mcp list
```

Se aparecer `Failed to send prompt` com `Cannot find module '@opencode-ai/plugin'`
nos registros, execute a instalação acima e feche e reabra o OpenCode.
Uma falha na instalação automática dessa biblioteca impede o carregamento
das ferramentas antes de a investigação começar.

Mantenha o JADX aberto na amostra, o plugin em 8650 e o MCP Streamable HTTP em
`http://127.0.0.1:8651/mcp`. `type: remote` descreve transporte HTTP, mesmo no
loopback. O estado conectado não garante que as consultas ao plugin funcionarão.

## Modelo e credencial

`opencode.json` usa o backend local da aula em `http://127.0.0.1:9931/v1` por
`@ai-sdk/openai-compatible`, isto é, Chat Completions. O modelo é o exemplo
`unsloth/GLM-4.7-Flash-GGUF:UD-Q4_K_XL`. Confira o ID realmente servido:

```powershell
(Invoke-RestMethod 'http://127.0.0.1:9931/v1/models').data.id
```

Se o backend exigir autenticação nessa consulta, use o cabeçalho exigido por ele.
Ajuste tanto a chave em `provider.laboratorio.models` quanto `model` no JSON.
`model` contém `laboratorio/` seguido do ID completo servido. O backend precisa
suportar chamadas de ferramentas. Esta rota usa JSON textual nas respostas dos
especialistas e não equivale ao `output_type` validado do SDK.

Se houver credencial, defina-a no mesmo terminal sem escrevê-la no JSON:

```powershell
$segredo = Read-Host 'Chave do backend' -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $segredo).Password
Remove-Variable segredo
```

Se o serviço local dispensar chave, defina um marcador local não secreto aceito
por ele, por exemplo `$env:OPENAI_API_KEY = 'local'`. Não use esse marcador em
serviços que exigem autenticação. Para outro provedor, configure `/connect` e
`/models` e ajuste ou remova o `model` local no JSON. O OpenCode não interpreta
automaticamente `OPENAI_BASE_URL` como esta configuração de provedor.

## Arquivos e acesso

O nome de cada arquivo `.opencode/agents/*.md` define o nome do agente.
O cabeçalho YAML define modo e permissões. O corpo contém o prompt.
`orquestrador` é `primary`. Os demais são `subagent`.

O padrão global é `"*": "deny"`. O orquestrador pode usar apenas `task` para
os três especialistas. Hunt e analista recebem explicitamente as 15 consultas
de leitura da lista LEITURA do laboratório, prefixadas com `jadx_`.
O analista também pode usar `reproduzir_transformacao`. Relator não recebe tools.
Nenhum agente recebe shell ou edição genérica de arquivos.
Não libere `jadx_*` como um todo: o servidor também tem ferramentas de alteração.
Confira os nomes expostos na versão instalada e mantenha a lista explícita.
As permissões limitam chamadas de ferramentas neste cliente, não outros clientes
conectados ao servidor, nem substituem isolamento do ambiente.

## Execução

Confirme o hash da cópia aberta no JADX, sem executar a amostra:

```powershell
(Get-FileHash -Algorithm SHA256 'C:\lab_jadx\amostra.apk').Hash
opencode --agent orquestrador
```

Substitua o caminho acima pelo arquivo real e envie na conversa:

```text
Investigue a amostra Android aberta no JADX, identificada pelo SHA-256
<cole o hash conferido>. Explique seu funcionamento em alto nível, investigue
trechos ofuscados ou potencialmente maliciosos e extraia IOCs com evidências.
Use hunt, analista e relator. Mantenha um dossiê com fontes, versões, cobertura
e limitações. Entregue o relatório e a tabela de IOCs para revisão humana.
```

O orquestrador envia o dossiê integral na tarefa de cada especialista. As sessões
filhas não recebem automaticamente o histórico completo do coordenador.
Resultados voltam pela resposta de `task`. Uma nova rodada do hunt exige nova
análise antes do relatório. A configuração não bloqueia essa ordem em código.
Evite chamar `@hunt` no exercício de equipe, pois a chamada manual pode iniciar
outra execução sem a coordenação prevista. Use `--agent orquestrador`.

## Transformações sobre bytes

A ferramenta em `.opencode/tools/reproduzir_transformacao.ts` usa um processo
Python fixo, recebe dados por stdin e chama `aplicar_receita` do módulo já existente.
Não oferece shell ao modelo nem aceita nome de programa ou código para executar.
Pode precisar do pacote `@opencode-ai/plugin`, gerenciado pelo OpenCode para as
ferramentas locais. O computador precisa conseguir resolver essa dependência.

Entrada sintética, sem achado da amostra:

```json
{
  "receita_json": "{\"entrada_hex\":\"59574a6a\",\"passos\":[{\"op\":\"base64_decode\"}]}",
  "fontes": ["E_DEMONSTRACAO"]
}
```

Resultado esperado: `saida_hex: "616263"`, `saida_utf8: "abc"`.
O script acrescenta receita, referências declaradas, resultado e ID T único em
`logs_transformacoes.jsonl`, numa localização fixa. O analista recebe esse registro.
O módulo conserva o limite de 64 KiB e 12 passos por receita e valida parâmetros.
Não há contador persistente de oito receitas por investigação nesta ponte.
As referências E são declaradas pelo modelo e exigem conferência humana.

## Dossiê e entrega

Peça evidências E com ferramenta, argumentos, classe, método e trecho literal.
Pistas P remetem a evidências, achados A remetem a pistas e IOCs I remetem a achados.
Use IDs únicos por execução e preserve versões anteriores nas revisitas.
Registre `versao_hunt` e `versao_analise`. O relator recebe a versão corrente inteira.
O JSON dos especialistas é texto solicitado no prompt. Esta rota não aplica
automaticamente os modelos Pydantic ou as conferências do programa Python.

Copie o relatório revisado da conversa para `relatorio_opencode.md` e registre
a tabela de IOCs em `iocs_opencode.csv`, preservando estados e referências.
Esses dois arquivos não são criados automaticamente pela configuração.
Guarde a versão do OpenCode, o modelo, o hash e os logs de cálculo, se houver.
Para preservar as sessões e os resultados de task, confira os IDs disponíveis:

```powershell
opencode session list
opencode export <id_da_sessao> > sessao_orquestrador.json
```

Repita a exportação para cada sessão filha relevante e confira se os retornos
das consultas estão presentes. A exportação não é o `fontes.json` auditado do SDK.
As fontes usadas pelos modelos seguem para o provedor configurado.
Nesta rota a revisão confere trechos, fontes, versões e completude manualmente.
Para aplicar os mesmos controles automáticos do SDK, implemente e teste uma
camada de validação de dossiê, referências e disponibilidade das etapas.

## Roteiro de revisão

1. Verifique os quatro agentes e a conexão MCP antes da missão.
2. Confira se as tarefas retornam ao orquestrador e se o relator recebe o dossiê.
3. Abra no JADX uma evidência de pista e uma evidência de IOC, se houver.
4. Compare estados, valores originais, cobertura e limitações com o relatório.
5. Se houver revisita, confira nova análise antes da redação final.
6. Registre qualquer trecho ausente, erro de interpretação ou etapa incompleta.

## Fontes

- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/permissions/
- https://opencode.ai/docs/mcp-servers/
- https://opencode.ai/docs/providers/
- https://opencode.ai/docs/custom-tools/
- https://opencode.ai/docs/cli/
