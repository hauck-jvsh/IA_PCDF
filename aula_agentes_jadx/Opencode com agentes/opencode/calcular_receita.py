"""Ponte fixa para as operações sobre bytes do laboratório da aula 02."""
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from transformacoes import aplicar_receita

def main():
    raw = sys.stdin.read(310001)
    if len(raw) > 310000:
        raise ValueError("Entrada excede o limite")
    pedido = json.loads(raw)
    if set(pedido) != {"receita_json", "fontes"}:
        raise ValueError("Use receita_json e fontes")
    fontes = pedido["fontes"]
    if not isinstance(fontes, list) or not 1 <= len(fontes) <= 20:
        raise ValueError("Cite entre 1 e 20 fontes")
    if any(not isinstance(f, str) or not 1 <= len(f) <= 200 for f in fontes):
        raise ValueError("Referência de fonte inválida")
    receita = pedido["receita_json"]
    if not isinstance(receita, str):
        raise ValueError("receita_json precisa ser texto JSON")
    resultado = aplicar_receita(receita)
    registro = {"registro_fonte": "T_" + uuid4().hex,
                "utc": datetime.now(timezone.utc).isoformat(),
                "fontes_declaradas": fontes, "receita": json.loads(receita),
                "resultado": resultado}
    with (ROOT / "logs_transformacoes.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    print(json.dumps(registro, ensure_ascii=False))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Receita recusada: {exc}", file=sys.stderr)
        sys.exit(1)
