import json
import sys
import unittest
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from chatbot import ChatbotAtendimento, registrar_historico  # noqa: E402


class ChatbotAtendimentoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bot = ChatbotAtendimento.de_arquivo(RAIZ / "base_conhecimento.json")

    def test_identifica_duvida_sobre_entrega(self):
        resposta = self.bot.responder("Qual é o prazo para minha entrega chegar?")
        self.assertEqual(resposta.intencao, "prazo_entrega")
        self.assertFalse(resposta.encaminhar_humano)
        self.assertGreaterEqual(resposta.confianca, 0.34)

    def test_identifica_forma_de_pagamento_sem_acentos(self):
        resposta = self.bot.responder("Posso parcelar o pagamento no cartao?")
        self.assertEqual(resposta.intencao, "formas_pagamento")

    def test_encaminha_pedido_explicito_para_humano(self):
        resposta = self.bot.responder("Quero falar com um atendente")
        self.assertEqual(resposta.intencao, "atendimento_humano")
        self.assertTrue(resposta.encaminhar_humano)

    def test_nao_inventa_resposta_para_assunto_desconhecido(self):
        resposta = self.bot.responder("Vocês vendem bicicletas elétricas?")
        self.assertEqual(resposta.intencao, "nao_identificada")
        self.assertTrue(resposta.encaminhar_humano)

    def test_registra_historico_em_jsonl(self):
        resposta = self.bot.responder("Posso fazer o pagamento com Pix?")
        arquivo = RAIZ / "tests" / ".historico-teste.jsonl"
        try:
            registrar_historico(arquivo, "cliente-demo", "Pagamento?", resposta)
            registro = json.loads(arquivo.read_text(encoding="utf-8"))
        finally:
            arquivo.unlink(missing_ok=True)
        self.assertEqual(registro["cliente_id"], "cliente-demo")
        self.assertEqual(registro["intencao"], "formas_pagamento")

    def test_rejeita_base_incompleta(self):
        with self.assertRaises(ValueError):
            ChatbotAtendimento({"empresa": "Teste"})


if __name__ == "__main__":
    unittest.main()
