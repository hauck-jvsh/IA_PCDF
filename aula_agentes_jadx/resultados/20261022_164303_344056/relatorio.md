# Relatório de análise de malware



SHA-256 informado pelo investigador: `ec033c13f06bcccb3d35b46c56003a60516339419ccc75a3738bbcf7f83e52b8`



Estado: rascunho para revisão do investigador.



## Resumo executivo

APK Android (SHA-256 ec033c13f06bcccb3d35b46c56003a60516339419ccc75a3738bbcf7f83e52b8), pacote raiz verifier.harmonizer.provider, 699 pacotes/3574 classes (árvore truncada), analisado estaticamente via JADX em 3 rodadas de hunt, 2 rodadas de análise aprofundada e 8 transformações determinísticas de decodificação. O conjunto de módulos é consistente com RAT bancário Android: serviço de acessibilidade com overlay/screenshot/gestos/exfiltração, envio silencioso de SMS, dump de contatos/SMS, canal de configuração remota Base64 ('empty|' inicial), download de payload disfarçado de atualização ('Searching for updates') e autodestruição via 'pm clear ' + packageName confirmada por decodificação XOR (T0007). Ofuscação em camadas: XOR com chave repetida (ac0.a→f11a.a), Base64, Unicode, nomes aleatórios e pacote profundo de decodificação. Indício de operação dirigida a falantes de português: _Login_title_ (Base64, I006) decodifica 'Serviço de Acessibilidade'. Presença no código não comprova execução, tráfego de rede nem autoria.



## Funcionamento em alto nível

1. [ESTÁTICO SUSTENTADO — A004/A005/I007] Config remota: zfyxetnpqczwwesatwnjdr.onStartCommand lê lqkgduyoofpqpmpsqmcean.ipqzpdjermcdvtbjxigpvizdmyv (inicial 'empty|'), decodifica entradas Base64 com charset XOR, popula kltwlkizuxhgjrcyfiarqyuwjuvz.x (pacotes-alvo overlay, minúsculas), configura módulos e inicia serviço foreground kiezkyvaplpxfgcszohglq; se a config começa com valor decodificado 'empty|'-like, desativa (wy.f(..., false)). 2. [HIPÓTESE] Origem da atualização da config (rede/C2) inferida do parsing e dos múltiplos consumidores via xrefs (M0031/M0041); classe escritora e endpoint não identificados. 3. [ESTÁTICO SUSTENTADO/PARCIAL — I004] Serviço de acessibilidade kltwlkizuxhgjrcyfiarqyuwjuvz: polling de rootInActiveWindow contra conjunto-alvo x, overlays WindowManager+FrameLayout/WebView, screenshots (takeScreenshot→Bitmap→WEBP/Base64), envio JSON via d0/wy, gestos e performAction(16); inicia httmqfkrvyaeiarpjzndtam via Intent (candidato a falso diálogo — baixa confiança). Retornos truncados (M0012/M0017) impediram leitura integral. 4. [ESTÁTICO SUSTENTADO — A001/I003] Serviço Response: valida scheme 'smsto' (XOR, T0001), extrai número (schemeSpecificPart) e corpo (extra 'android.intent.extra.TEXT', T0002), envia SMS silencioso via SmsManager.getDefault().sendTextMessage sem PendingIntent, try/catch silencioso, stopSelf + START_NOT_STICKY. Gatilho NÃO confirmado (manifesto indisponível); consistência com resposta automática de mensagens é inferência. 5. [ESTÁTICO PARCIAL — A003] r0: query a ContactsContract.CommonDataKinds.Phone e URIs de SMS decodificadas em runtime, dump concatenado; método truncado (M0029), uso integral de SmsManager não visível. 6. [ESTÁTICO PARCIAL — P009] DownloadForegroundService: HttpURLConnection/URL/FileOutputStream, serviço foreground com notificação; disfarce 'Searching for updates' (string decodificada, T0008 — candidato, associação byte-a-byte não revalidada); URL real não extraída (candidato — string XOR de 21 bytes não reproduzida). 7. [ESTÁTICO SUSTENTADO — A008/I001/I005] Autodestruição cafaiezlhmdcjcdp: Runtime.exec('pm clear ' + packageName) — decodificação XOR confirmada por T0007; deleção recursiva de filesDir/arquivos e bancos; System.exit(1); método b alterna flags do serviço de acessibilidade (kltwlkizuxhgjrcyfiarqyuwjuvz.b0). Gatilho NÃO determinado. 8. [ESTÁTICO SUSTENTADO — A007/P002/P010] Ofuscação em camadas: XOR com chave repetida (ac0.a→f11a.a; f11a não localizada — M0043/M0044 404 — validação indireta pelas transformações), Base64 na config, Unicode, nomes de classes/campos aleatórios, pacote profundo a.b.c...bababa. 9. [NÃO EXAMINADO] Carregamento dinâmico (DexClassLoader sem resultados, M0008), reflexão, loadLibrary, BOOT_COMPLETED (sem resultados, M0030 — ausência de literal não descarta receiver), NotificationListenerService não verificado.



## Fluxo reconstruído

1. 1. Config remota (lqkgduyoofpqpmpsqmcean.ipqzpdjermcdvtbjxigpvizdmyv / ALL_CONFIG) é lida por zfyxetnpqczwwesatwnjdr.onStartCommand, decodificada em Base64 e preenche o conjunto-alvo kltwlkizuxhgjrcyfiarqyuwjuvz.x (pacotes overlay).

2. 2. Serviço de acessibilidade monitora janela ativa, aplica overlays WebView sobre pacotes em x, captura screenshots (Base64/WEBP) e envia JSON via d0/wy.

3. 3. Serviço Response recebe Intent com URI scheme 'smsto' e extra 'android.intent.extra.TEXT' e envia SMS silencioso via SmsManager.getDefault().sendTextMessage, parando a si (stopSelf, return 2).

4. 4. r0 consulta ContactsContract/URIs de SMS decodificadas em runtime para dump de contatos/mensagens (corpo truncado).

5. 5. DownloadForegroundService usa HttpURLConnection/URL com strings decodificadas, incluindo 'Searching for updates' (texto disfarçado de atualização), para baixar payload.

6. 6. Activity cafaiezlhmdcjcdp.e executa Runtime.getRuntime().exec('pm clear ' + packageName), apaga recursivamente arquivos/bancos e chama System.exit(1) — autodestruição por limpeza de dados.



## Achados

### A001

Serviço Response: onStartCommand chama a(intent), que valida o scheme da URI do Intent contra string decodificada por XOR ('smsto'), extrai schemeSpecificPart como número e o extra 'android.intent.extra.TEXT' como corpo, e envia SMS silencioso (sem PendingIntent). Depois stopSelf e return 2 (START_NOT_STICKY). Fluxo reconstruído estáticamente; gatilho externo não confirmado (manifesto indisponível).

Estado: sustentado_no_codigo. Confiança: alta.

Fonte M0006: verifier.harmonizer.provider.Response, a

```text

SmsManager.getDefault().sendTextMessage(schemeSpecificPart, null, stringExtra, null, null);

```

Fonte M0006: verifier.harmonizer.provider.Response, onStartCommand

```text

a(intent); stopSelf(i2); return 2;

```

Fonte M0006: verifier.harmonizer.provider.Response, a

```text

Uri data = intent.getData(); String schemeSpecificPart = (data == null || !ac0.a(new byte[]{80, -115, -75, -17, 25}, new byte[]{35, -32, -58, -101, 118, 98, 2, 2}).equals(data.getScheme())) ? null : data.getSchemeSpecificPart();

```

Lacuna: AndroidManifest.xml indisponível (M0002): gatilho/intent-filter do serviço não confirmado.

### A003

Segundo uso de SmsManager na classe r0: importa SmsManager, SubscriptionManager e ContactsContract e executa query ao ContentResolver sobre ContactsContract.CommonDataKinds.Phone.CONTENT_URI, consistente com dump de contatos/SMS. Corpo do método truncado em M0029; uso integral de SmsManager em r0 não visível.

Estado: sustentado_no_codigo. Confiança: media.

Fonte M0005: -, -

```text

items: ["verifier.harmonizer.provider.Response", "verifier.harmonizer.provider.r0"]

```

Fonte M0029: verifier.harmonizer.provider.r0, a

```text

import android.telephony.SmsManager;

```

Fonte M0029: verifier.harmonizer.provider.r0, a

```text

Query = context.getContentResolver().query(ContactsContract.CommonDataKinds.Phone.CONTENT_URI, new

```

Lacuna: M0029 truncado: final do método a() e envio/exfiltração do dump não vistos.

### A004

Canal de configuração remota: zfyxetnpqczwwesatwnjdr.onStartCommand valida lqkgduyoofpqpmpsqmcean.ipqzpdjermcdvtbjxigpvizdmyv (inicial 'empty|'), decodifica entradas Base64 separadas por delimitador decodificado, popula kltwlkizuxhgjrcyfiarqyuwjuvz.x (pacotes-alvo overlay, em minúsculas) e configura módulos; inicia serviço foreground kiezkyvaplpxfgcszohglq via startForegroundService. Se a config começa com valor decodificado de 'empty|'-like ou igual ao primeiro item, desativa via wy.f(..., false).

Estado: sustentado_no_codigo. Confiança: alta.

Fonte M0024: verifier.harmonizer.provider.zfyxetnpqczwwesatwnjdr, onStartCommand

```text

if (!lqkgduyoofpqpmpsqmcean.ipqzpdjermcdvtbjxigpvizdmyv.contains(ac0.a(new byte[]{64}, new byte[]{60, -62, 14, 96, -109, -109, -73, -65})) || lqkgduyoofpqpmpsqmcean.ipqzpdjermcdvtbjxigpvizdmyv.startsWith(ac0.a(new byte[]{-48, -80, -115, -76, -102, -36}, new byte[]{-75, -35, -3, -64, -29, -96, 103, 8}))) {

```

Fonte M0024: verifier.harmonizer.provider.zfyxetnpqczwwesatwnjdr, onStartCommand

```text

String str2 = new String(Base64.decode(str, 0), ac0.a(new byte[]{-11, -119, 100, -61, -97}, new byte[]{-96, -35, 34, -18, -89, -90, -7, 46}));

```

Fonte M0024: verifier.harmonizer.provider.zfyxetnpqczwwesatwnjdr, onStartCommand

```text

kltwlkizuxhgjrcyfiarqyuwjuvz.x.add(str5.toLowerCase());

```

Fonte M0024: verifier.harmonizer.provider.zfyxetnpqczwwesatwnjdr, onStartCommand

```text

startForegroundService(intent2);

```

Lacuna: Origem da atualização de ipqzpdjermcdvtbjxigpvizdmyv/ALL_CONFIG (rede/C2) não mapeada.

### A005

Classe de configuração central lqkgduyoofpqpmpsqmcean: campos indicativos (_Login_title_, _Login_btn_, Anti_Delete, ALL_CONFIG, Prevent_sleep, SetDef_SMS, SetDef_Call, extjs, PPKG, subdir) e ipqzpdjermcdvtbjxigpvizdmyv = "empty|" como estado inicial (módulos desativados até config remota). _Login_title_ = 'U2VydmnDp28gZGUgQWNlc3NpYmlsaWRhZGU=' (Base64 de texto em português sobre acessibilidade), indicando phishing de permissão de acessibilidade em pt-BR.

Estado: sustentado_no_codigo. Confiança: alta.

Fonte M0025: verifier.harmonizer.provider.lqkgduyoofpqpmpsqmcean, <fields>

```text

AccessInfo: FIELD 0x9 (public static ) java.lang.String Anti_Delete

```

Fonte M0025: verifier.harmonizer.provider.lqkgduyoofpqpmpsqmcean, <fields>

```text

AccessInfo: FIELD 0x9 (public static ) java.lang.String SetDef_SMS

```

Fonte M0028: verifier.harmonizer.provider.lqkgduyoofpqpmpsqmcean, <clinit>

```text

public static String ipqzpdjermcdvtbjxigpvizdmyv = "empty|";

```

Fonte M0028: verifier.harmonizer.provider.lqkgduyoofpqpmpsqmcean, <clinit>

```text

public static String _Login_title_ = "U2VydmnDp28gZGUgQWNlc3NpYmlsaWRhZGU=";

```

Lacuna: Valores finais dos campos de config dependem da atualização remota, não observável estaticamente.

### A007

Ofuscação estrutural: nomes de classes/campos artificialmente aleatórios (kltwlkizuxhgjrcyfiarqyuwjuvz, lqkgduyoofpqpmpsqmcean, rddzaiebmeaottxhlopuliu), pacote de decodificação profundo (a.b.c.d...bababa) com classes curtas (ac0, bc0, wy, qe, ce), strings XOR em <clinit> (inclusive no AsyncTask kiezkyvaplpxfgcszohglq$d via smali).

Estado: sustentado_no_codigo. Confiança: alta.

Fonte M0038: verifier.harmonizer.provider.o0, <imports>

```text

import a.b.c.d.e.f.g.h.i.j.k.l.m.o.p.aa.aaa.aaaa.aaab.aabb.aabbaa.ababaa.bababa.ac0;

```

Fonte M0028: verifier.harmonizer.provider.lqkgduyoofpqpmpsqmcean, <clinit>

```text

public static String rddzaiebmeaottxhlopuliu = get_dropname();

```

Fonte M0036: verifier.harmonizer.provider.kiezkyvaplpxfgcszohglq.d, <clinit>

```text

.class public Lverifier/harmonizer/provider/kiezkyvaplpxfgcszohglq$d;
.super Landroid/os/AsyncTask;

```

### A008

Autodestruição confirmada com decodificação: cafaiezlhmdcjcdp.e executa Runtime.getRuntime().exec(comando_decodificado + packageName); a transformação XOR determinística (T0007) reproduz o comando decodificado como 'pm clear ', resultando em 'pm clear <pacote>' — limpeza total dos dados do próprio app via shell (apaga config, bancos e artefatos). Em seguida apaga recursivamente filesDir e chama System.exit(1). O método b alterna flags do serviço de acessibilidade (kltwlkizuxhgjrcyfiarqyuwjuvz.b0).

Estado: sustentado_no_codigo. Confiança: alta.

Fonte M0042: verifier.harmonizer.provider.cafaiezlhmdcjcdp, e

```text

Runtime.getRuntime().exec(ac0.a(new byte[]{-3, 105, 2, 102, 116, 114, 102, 122, -83}, new byte[]{-115, 4, 34, 5, 24, 23, 7, 8}) + getApplicationContext().getPackageName());

```

Fonte T0007: -, -

```text

{"saida_hex": "706d20636c65617220", "saida_utf8": "pm clear ", "passos": [{"op": "xor", "saida_hex": "706d20636c65617220"}]}

```

Fonte M0042: verifier.harmonizer.provider.cafaiezlhmdcjcdp, e

```text

c(applicationContext.getFilesDir());

```

Fonte M0042: verifier.harmonizer.provider.cafaiezlhmdcjcdp, e

```text

System.exit(1);

```

Fonte M0042: verifier.harmonizer.provider.cafaiezlhmdcjcdp, b

```text

kltwlkizuxhgjrcyfiarqyuwjuvz.b0 = z;

```

Lacuna: Gatilho que invoca cafaiezlhmdcjcdp.e (quando a autodestruição é disparada) não determinado; manifesto indisponível.

Lacuna: Nem toda string da activity (demais mensagens/flags) foi decodificada — limite de receitas atingido.



## IOCs

Valores exatos e estados em iocs.csv e analise.json.

- I001: comando_shell, `pm clear <packageName>`, sustentado_no_codigo, confiança alta. Papel: autodestruição: limpeza dos dados do próprio app concatenado com getPackageName() em Runtime.exec.

- I003: classe_maliciosa, `verifier.harmonizer.provider.Response`, sustentado_no_codigo, confiança alta. Papel: serviço de envio silencioso de SMS via SmsManager.

- I004: classe_maliciosa, `verifier.harmonizer.provider.kltwlkizuxhgjrcyfiarqyuwjuvz (AccessibilityService)`, sustentado_no_codigo, confiança media. Papel: serviço de acessibilidade: overlay, screenshot, gestos/cliques e exfiltração de UI; conjunto-alvo x alimentado pela config remota.

- I005: classe_maliciosa, `verifier.harmonizer.provider.cafaiezlhmdcjcdp`, sustentado_no_codigo, confiança alta. Papel: activity de autodestruição: 'pm clear' via shell, deleção recursiva de arquivos e System.exit(1).

- I006: config_base64, `U2VydmnDp28gZGUgQWNlc3NpYmlsaWRhZGU= (campo _Login_title_, Base64; decodifica para texto em português sobre 'Serviço de Acessibilidade')`, sustentado_no_codigo, confiança alta. Papel: título de tela de phishing de habilitação de acessibilidade (pt-BR).

- I007: chave_config_inicial, `empty|`, sustentado_no_codigo, confiança alta. Papel: valor inicial de ipqzpdjermcdvtbjxigpvizdmyv — config vazia, módulos desativados até recebimento remoto.



## Cobertura

- servico_sms_Response: examinada. Fonte completa em M0006; fluxo onStartCommand → a() → SmsManager → stopSelf reconstruído.

- ofuscacao_ac0_xor: examinada. Algoritmo XOR validado por transformações determinísticas T0007 ('pm clear ') e T0008 ('Searching for updates'); delegação ac0→f11a em M0010. Corpo de f11a não obtido (M0043/M0044, 404).

- autodestruicao_cafaiezlhmdcjcdp: examinada. Comando shell decodificado ('pm clear '), deleção de filesDir e System.exit(1) confirmados (M0042 + T0007); gatilho de invocação ainda não mapeado.

- configuracao_remota_e_C2: parcial. Parsing Base64, campos e consumidores de ALL_CONFIG/ipqzpdjermcdvtbjxigpvizdmyv confirmados; fonte de atualização (rede) não seguida até o fim.

- servico_acessibilidade_kltwlkizuxhgjrcyfiarqyuwjuvz: parcial. Capacidades gerais (overlay, screenshot, gestos, exfiltração) confirmadas em rodadas anteriores; retornos truncados (M0012/M0017) impediram leitura integral.

- classe_r0_dump_sms_contatos: parcial. Imports e query a ContactsContract confirmados (M0029); método truncado.

- rede_e_exfiltracao: parcial. DownloadForegroundService com HttpURLConnection/URL e string de disfarce decodificada; URLs/domínios reais não extraídos; d0/o0 apenas candidatos.

- manifest_e_entry_points: nao_examinada. AndroidManifest.xml indisponível (M0002 erro 404); entry points, permissões e intents-filters não confirmados.

- carregamento_dinamico_e_reflexao: nao_examinada. M0008 sem itens para DexClassLoader; reflexão/loadLibrary não pesquisados.



## Limitações

- Análise puramente estática via JADX: presença no código não comprova execução, atividade de rede nem autoria.

- AndroidManifest.xml indisponível (M0002, erro 404): gatilhos, permissões e intent-filters não confirmados.

- M0043/M0044 falharam (404): classe f11a (implementação do XOR) não localizada pelo índice; o algoritmo foi validado indiretamente pelas transformações T0007/T0008.

- A ferramenta de transformações atingiu o limite de 8 receitas: a maioria das strings ofuscadas (scheme 'smsto', extras, URL de download, listas-alvo, demais mensagens) permanece não decodificada nesta rodada.

- A correspondência byte-a-byte entre o array de DownloadForegroundService.<clinit> (M0039) e T0008 não foi revalidada (falha de receita por limite); associação registrada como candidato.

- Retornos truncados (M0012, M0016, M0017, M0020, M0029, M0033, M0036, M0038, M0039) deixaram partes relevantes não examinadas.

- M0032 vazio e M0034 sem corpo: lógica interna do AsyncTask kiezkyvaplpxfgcszohglq.d não lida.

- Nenhum domínio C2 ou URL literal foi extraído; a busca por 'https://' retornou vazia (M0021), o que não descarta comunicação C2.

- Pista P002 sem achado com evidência conferida; permanece pendente.

- Pista P009 sem achado com evidência conferida; permanece pendente.

- AndroidManifest.xml indisponível (M0002, erro 404): entry points, permissões (SEND_SMS, BIND_ACCESSIBILITY_SERVICE etc.) e intent-filters não confirmados; gatilhos do serviço Response (A001) e da autodestruição (A008) não determinados.

- Retornos truncados: M0001 (árvore), M0012/M0017 (serviço de acessibilidade), M0020 (d0), M0029 (r0), M0033, M0036 (smali do AsyncTask), M0038 (o0), M0039 (DownloadForegroundService) — partes relevantes não examinadas.

- M0032 vazio e M0034 sem corpo: lógica interna do AsyncTask kiezkyvaplpxfgcszohglq.d não lida; M0035 falhou (404).

- Classe f11a (implementação XOR) não localizada pelo índice (M0043/M0044, 404); algoritmo validado apenas indiretamente pelas transformações determinísticas.

- Limite de 8 receitas de transformação: a maioria das strings ofuscadas (listas-alvo x, URL de download, demais mensagens) permanece não decodificada.

- IOC de rede AUSENTE: nenhum domínio/URL/IP literal extraído; busca por 'https://' vazia (M0021); URL provavelmente XOR-ofuscada. Ausência de literais não descarta comunicação C2 (M0021, M0030).

- IOCs candidatos de baixa confiança não incluídos no índice de IOCs sustentados: httmqfkrvyaeiarpjzndtam (falso diálogo) e string XOR de 21 bytes do DownloadForegroundService (URL) — registrar como candidatos apenas.

- Pistas P002 e P009 permanecem sem achado com evidência conferida; mantidas como pistas.

- Consulta M0026 falhou (campo tratado como método); ipqzpdjermcdvtbjxigpvizdmyv é campo estático.



## Próximos passos

- Obter AndroidManifest.xml por via alternativa (extração direta do APK com apktool/androguard) para confirmar entry points, permissões e intent-filters, inclusive o gatilho do serviço Response (A001/I003).

- Decodificar as strings XOR restantes reimplementando o algoritmo ac0.a/f11a.a localmente (sem limite de receitas), em especial a string de 21 bytes de DownloadForegroundService (possível URL de C2/download) e as listas-alvo de kltwlkizuxhgjrcyfiarqyuwjuvz.x.

- Examinar integralmente r0 (M0029 truncado) para confirmar dump de contatos/SMS e o destino/exfiltração dos dados.

- Mapear a origem da atualização de ipqzpdjermcdvtbjxigpvizdmyv/ALL_CONFIG (classe escritora e endpoint de rede) — hipótese (a) —, inclusive via xrefs adicionais e análise de d0/o0/wy.

- Determinar o gatilho da rotina de autodestruição cafaiezlhmdcjcdp.e (A008/I005) e as condições de invocação.

- Verificar httmqfkrvyaeiarpjzndtam como tela de overlay/falso diálogo (candidato, baixa confiança).

- Pesquisar carregamento dinâmico, reflexão, loadLibrary e receivers (DexClassLoader, BOOT_COMPLETED) com buscas complementares.

- Validar em sandbox (dinâmico) a execução dos módulos: envio silencioso de SMS, overlay, screenshot WEBP/Base64 e 'pm clear' — presença estática não comprova execução.