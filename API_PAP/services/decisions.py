# -*- coding: utf-8 -*-
from typing import Dict, Optional

DECISIONS: Dict[str, Dict[str, str]] = {
    "Solo": {
        "acao": "Ligar a bomba de irrigação até atingir 60–80% da capacidade de campo",
        "acao_alt": "Agendar irrigação emergencial",
    },
    "Clima": {
        "acao": "Aplicar proteção: sombrite contra calor ou medidas anti-geada conforme o caso",
        "acao_alt": "Reprogramar atividades sensíveis ao clima",
    },
    "Sensor": {
        "acao": "Verificar alimentação elétrica/estrutura e restabelecer condições do sensor",
        "acao_alt": "Remoto: reiniciar o sensor",
    },
    "Praga": {
        "acao": "Aplicar protocolo de controlo de pragas conforme rótulo e monitorar 24h",
        "acao_alt": "Isolar a área afetada e recolher amostras",
    },
}

def format_decision_text(tipo: str, acao: str, acao_alt: str) -> str:
    return f"Alerta: {tipo} - Tomada de decisão: {acao}/{acao_alt}"

def build_alert(tipo: str, mensagem: str, severidade: str,
                acao: Optional[str] = None, acao_alt: Optional[str] = None,
                acao_codigo: Optional[str] = None) -> Dict[str, str]:
    base = DECISIONS.get(tipo, {})
    act  = acao or base.get("acao") or "Ver detalhes no painel"
    alt  = acao_alt or base.get("acao_alt") or "Contactar suporte"
    alert = {
        "tipo": tipo,
        "mensagem": mensagem,
        "severidade": severidade,
        "acao": act,
        "acao_alt": alt,
        "decisao_texto": format_decision_text(tipo, act, alt),
    }
    if acao_codigo:
        alert["acao_codigo"] = acao_codigo
    return alert

