"""Núcleo de um assistente virtual com base de conhecimento e fallback humano."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LIMIAR_CONFIANCA = 0.34
PEDIDOS_HUMANOS = (
    "falar com atendente",
    "falar com um atendente",
    "falar com humano",
    "falar com uma pessoa",
    "pessoa real",
    "quero atendente",
)


def normalizar(texto: str) -> str:
    """Remove acentos e pontuação para tornar a busca mais tolerante."""
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )
    return " ".join(re.sub(r"[^a-zA-Z0-9 ]", " ", sem_acentos.lower()).split())


@dataclass(frozen=True)
class Resposta:
    mensagem: str
    intencao: str
    confianca: float
    encaminhar_humano: bool

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChatbotAtendimento:
    """Classifica perguntas por palavras-chave sem inventar informações."""

    def __init__(self, base: dict[str, Any]) -> None:
        self.base = self._validar_base(base)

    @classmethod
    def de_arquivo(cls, caminho: str | Path) -> "ChatbotAtendimento":
        with Path(caminho).open(encoding="utf-8") as arquivo:
            return cls(json.load(arquivo))

    @staticmethod
    def _validar_base(base: dict[str, Any]) -> dict[str, Any]:
        obrigatorios = {"empresa", "mensagem_fallback", "intencoes"}
        ausentes = obrigatorios.difference(base)
        if ausentes:
            raise ValueError(f"Campos ausentes na base: {', '.join(sorted(ausentes))}")
        if not isinstance(base["intencoes"], list) or not base["intencoes"]:
            raise ValueError("A base precisa conter ao menos uma intenção.")
        for item in base["intencoes"]:
            if not all(chave in item for chave in ("nome", "palavras_chave", "resposta")):
                raise ValueError("Cada intenção precisa de nome, palavras_chave e resposta.")
        return base

    def responder(self, mensagem: str) -> Resposta:
        texto = normalizar(mensagem)
        if not texto:
            return self._fallback()

        if any(expressao in texto for expressao in PEDIDOS_HUMANOS):
            return Resposta(
                mensagem="Claro. Vou encaminhar seu atendimento para uma pessoa da equipe.",
                intencao="atendimento_humano",
                confianca=1.0,
                encaminhar_humano=True,
            )

        termos_mensagem = set(texto.split())
        melhor_item: dict[str, Any] | None = None
        melhor_pontuacao = 0.0

        for item in self.base["intencoes"]:
            palavras = [normalizar(palavra) for palavra in item["palavras_chave"]]
            acertos = sum(
                1
                for palavra in palavras
                if palavra in texto or palavra in termos_mensagem
            )
            pontuacao = acertos / max(2, len(palavras))
            if pontuacao > melhor_pontuacao:
                melhor_item = item
                melhor_pontuacao = pontuacao

        if melhor_item is None or melhor_pontuacao < LIMIAR_CONFIANCA:
            return self._fallback()

        return Resposta(
            mensagem=melhor_item["resposta"],
            intencao=melhor_item["nome"],
            confianca=round(melhor_pontuacao, 2),
            encaminhar_humano=False,
        )

    def _fallback(self) -> Resposta:
        return Resposta(
            mensagem=self.base["mensagem_fallback"],
            intencao="nao_identificada",
            confianca=0.0,
            encaminhar_humano=True,
        )


def registrar_historico(
    caminho: str | Path,
    cliente_id: str,
    mensagem: str,
    resposta: Resposta,
) -> None:
    """Registra eventos em JSONL; o identificador deve ser interno e não sensível."""
    registro = {
        "data_hora": datetime.now(timezone.utc).isoformat(),
        "cliente_id": cliente_id,
        "mensagem": mensagem,
        "resposta": resposta.mensagem,
        "intencao": resposta.intencao,
        "confianca": resposta.confianca,
        "encaminhar_humano": resposta.encaminhar_humano,
    }
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")


def executar_cli() -> None:
    parser = argparse.ArgumentParser(description="Demonstração de chatbot de atendimento")
    parser.add_argument("mensagem", help="Mensagem enviada pelo cliente")
    parser.add_argument("--cliente", default="demonstracao", help="Identificador interno")
    parser.add_argument(
        "--base",
        default=Path(__file__).with_name("base_conhecimento.json"),
        type=Path,
        help="Arquivo JSON com a base de conhecimento",
    )
    parser.add_argument("--historico", type=Path, help="Arquivo JSONL opcional para auditoria")
    argumentos = parser.parse_args()

    bot = ChatbotAtendimento.de_arquivo(argumentos.base)
    resposta = bot.responder(argumentos.mensagem)
    if argumentos.historico:
        registrar_historico(
            argumentos.historico,
            argumentos.cliente,
            argumentos.mensagem,
            resposta,
        )
    print(json.dumps(resposta.como_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    executar_cli()
