"""API HTTP mínima para integrar o assistente a sites, CRMs ou mensageria."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from chatbot import ChatbotAtendimento


class ManipuladorChatbot(BaseHTTPRequestHandler):
    bot: ChatbotAtendimento

    def _enviar(self, status: HTTPStatus, conteudo: dict) -> None:
        corpo = json.dumps(conteudo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._enviar(HTTPStatus.OK, {"status": "ok"})
            return
        self._enviar(HTTPStatus.NOT_FOUND, {"erro": "Rota não encontrada"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/mensagens":
            self._enviar(HTTPStatus.NOT_FOUND, {"erro": "Rota não encontrada"})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            dados = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            mensagem = dados.get("mensagem")
            if not isinstance(mensagem, str) or not mensagem.strip():
                raise ValueError("O campo 'mensagem' é obrigatório.")
        except (ValueError, json.JSONDecodeError) as erro:
            self._enviar(HTTPStatus.BAD_REQUEST, {"erro": str(erro)})
            return

        self._enviar(HTTPStatus.OK, self.bot.responder(mensagem).como_dict())

    def log_message(self, formato: str, *argumentos: object) -> None:
        return


def executar() -> None:
    parser = argparse.ArgumentParser(description="API do chatbot de atendimento")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument(
        "--base",
        type=Path,
        default=Path(__file__).with_name("base_conhecimento.json"),
    )
    argumentos = parser.parse_args()
    ManipuladorChatbot.bot = ChatbotAtendimento.de_arquivo(argumentos.base)
    servidor = ThreadingHTTPServer(("127.0.0.1", argumentos.porta), ManipuladorChatbot)
    print(f"API disponível em http://127.0.0.1:{argumentos.porta}")
    servidor.serve_forever()


if __name__ == "__main__":
    executar()
