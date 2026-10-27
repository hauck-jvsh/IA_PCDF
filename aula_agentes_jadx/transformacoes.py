"""Operações fechadas sobre bytes. Não avalia código nem acessa arquivos/rede."""
import base64
import hashlib
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

MAX_BYTES = 65536
MAX_PASSOS = 12

def ler_bytes(origem: dict, nome: str) -> bytes:
    """Lê `<nome>_hex` ou `<nome>_bytes`.

    `_bytes` aceita a lista como aparece no Java, com sinal (new byte[]{110, -117}),
    para o modelo não precisar converter dezenas de valores para hexadecimal.
    """
    if f"{nome}_bytes" in origem:
        valores = origem[f"{nome}_bytes"]
        if not isinstance(valores, list) or not all(
                isinstance(v, int) and -128 <= v <= 255 for v in valores):
            raise ValueError(f"{nome}_bytes deve ser uma lista de inteiros entre -128 e 255")
        return bytes(v & 0xFF for v in valores)
    try:
        return bytes.fromhex(origem[f"{nome}_hex"])
    except KeyError:
        raise ValueError(f"Informe {nome}_hex ou {nome}_bytes") from None
    except ValueError:
        raise ValueError(f"{nome}_hex deve conter só 0-9 e a-f. Para arrays Java "
                         f"como new byte[]{{110, -117}}, use {nome}_bytes") from None

def aplicar_receita(receita_json: str) -> dict:
    if len(receita_json) > 300000:
        raise ValueError("Receita excede o limite")
    receita = json.loads(receita_json)
    if len(set(receita) & {"entrada_hex", "entrada_bytes"}) != 1 or "passos" not in receita:
        raise ValueError("Use passos e entrada_hex ou entrada_bytes")
    dados = ler_bytes(receita, "entrada")
    passos = receita["passos"]
    if not isinstance(passos, list) or len(passos) > MAX_PASSOS:
        raise ValueError("Até 12 operações por receita")
    trilha = []
    for passo in passos:
        if len(dados) > MAX_BYTES:
            raise ValueError("Entrada maior que 64 KiB")
        if not isinstance(passo, dict) or "op" not in passo:
            raise ValueError('Cada passo deve ser um objeto com "op", por exemplo '
                             '{"op": "base64_decode"} ou {"op": "xor", "chave_hex": "2a"}')
        op = passo["op"]
        if op == "base64_decode":
            dados = base64.b64decode(dados, validate=True)
        elif op == "hex_decode":
            dados = bytes.fromhex(dados.decode("ascii"))
        elif op in {"md5", "sha1", "sha256", "sha512"}:
            dados = hashlib.new(op, dados).digest()
        elif op == "pbkdf2_hmac":
            n, tamanho = int(passo["iteracoes"]), int(passo["tamanho"])
            if not 1 <= n <= 1000000 or not 1 <= tamanho <= 64:
                raise ValueError("Parâmetros de derivação fora do limite")
            hash_nome = passo["hash"]
            if hash_nome not in {"sha1", "sha256", "sha512"}:
                raise ValueError("Hash não permitido para derivação")
            sal = bytes.fromhex(passo["sal_hex"])
            if len(sal) > 1024:
                raise ValueError("Sal maior que 1024 bytes")
            dados = hashlib.pbkdf2_hmac(hash_nome, dados, sal, n, tamanho)
        elif op == "xor":
            chave = ler_bytes(passo, "chave")
            if not chave or len(chave) > MAX_BYTES:
                raise ValueError("Chave XOR inválida")
            dados = bytes(b ^ chave[i % len(chave)] for i, b in enumerate(dados))
        elif op == "aes_cbc_decrypt":
            chave = bytes.fromhex(passo["chave_hex"])
            iv = bytes.fromhex(passo["iv_hex"])
            if len(chave) not in (16, 24, 32) or len(iv) != 16:
                raise ValueError("Tamanho de chave ou IV inválido")
            decifrador = Cipher(algorithms.AES(chave), modes.CBC(iv)).decryptor()
            dados = decifrador.update(dados) + decifrador.finalize()
        elif op == "unpad_pkcs7":
            unpadder = PKCS7(128).unpadder()
            dados = unpadder.update(dados) + unpadder.finalize()
        elif op == "slice":
            inicio, fim = int(passo["inicio"]), int(passo["fim"])
            if not 0 <= inicio <= fim <= len(dados):
                raise ValueError("Recorte inválido")
            dados = dados[inicio:fim]
        else:
            raise ValueError("Operação não implementada: " + str(op))
        trilha.append({"op": op, "saida_hex": dados.hex()})
    if len(dados) > MAX_BYTES:
        raise ValueError("Resultado maior que 64 KiB")
    try:
        texto = dados.decode("utf-8")
    except UnicodeDecodeError:
        texto = None
    return {"saida_hex": dados.hex(), "saida_utf8": texto, "passos": trilha}
