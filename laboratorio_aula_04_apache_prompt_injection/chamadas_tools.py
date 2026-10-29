"""Adaptador técnico compartilhado: SDK e chamada JSON de ferramentas.

Este módulo não define missão, catálogo, permissões ou laço de nenhum agente.
"""
import json
import os
from urllib.parse import urlsplit
from openai import APIStatusError, DefaultHttpxClient, OpenAI

def chamar_modelo(mensagens, ferramentas):
    base = os.environ.get('OPENAI_BASE_URL', '').rstrip('/')
    modelo = os.environ.get('OPENAI_MODEL', '')
    if not base or not modelo:
        raise ValueError('Defina OPENAI_BASE_URL (incluindo /v1) e OPENAI_MODEL. Ou use --modo ensaio.')
    partes = urlsplit(base)
    if partes.scheme not in ('https', 'http') or not partes.hostname or partes.username or partes.password or partes.query or partes.fragment:
        raise ValueError('OPENAI_BASE_URL inválida.')
    if partes.scheme == 'http' and partes.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('HTTP permitido apenas em loopback. Use HTTPS para provedor remoto.')
    try:
        with OpenAI(
            base_url=base,
            api_key=os.environ.get('OPENAI_API_KEY') or 'sem-chave-local',
            timeout=60.0,
            max_retries=0,
            http_client=DefaultHttpxClient(follow_redirects=False),
        ) as cliente:
            resposta = cliente.chat.completions.create(
                model=modelo,
                messages=mensagens,
                tools=ferramentas,
                tool_choice='auto',
                store=False,
            )
            return resposta.choices[0].message.model_dump(exclude_none=True)
    except APIStatusError as e:
        raise RuntimeError(f'Provedor retornou HTTP {e.status_code}. Confira URL, modelo e suporte a tools.') from None


def processar_chamada(chamada, executar_ferramenta):
    """Decodifica a chamada; a autorização pertence ao executor de cada agente."""
    try:
        if not isinstance(chamada, dict) or chamada.get('type') != 'function':
            raise ValueError('Tipo de ferramenta não autorizado.')
        funcao = chamada['function']
        nome = funcao['name']
        texto = funcao['arguments']
        if not isinstance(nome, str) or not isinstance(texto, str) or len(texto) > 32000:
            raise ValueError('Nome ou argumentos inválidos.')
        argumentos = json.loads(texto)
        retorno = executar_ferramenta(nome, argumentos)
        if not isinstance(retorno, dict):
            raise ValueError('Retorno de ferramenta deve ser um objeto JSON.')
        return retorno
    except (ValueError, KeyError, TypeError) as erro:
        return {'erro': str(erro)}
