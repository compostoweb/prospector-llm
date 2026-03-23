"""
services/lead_scorer.py

Calcula o score de qualidade de um lead (0–100) baseado nos dados disponíveis.

Critérios e pesos:
  has_linkedin_url           → +20  (essencial para canais de prospecção)
  has_corporate_email        → +25  (crítico para canal de e-mail)
  email_corporate_verified   → +10  (confirmado via ZeroBounce)
  has_company                → +10  (empresa identificada)
  has_website                → +10  (sinal de empresa formal)
  has_phone                  → +5   (dado complementar)
  has_segment                → +10  (segmento identificado — melhora personalização)
  has_city                   → +5   (permite personalização por região)
  has_personal_email_only    → −5   (e-mail pessoal reduz confiança no contato)

Score máximo: 95 (todos os critérios positivos, sem penalidade)
Score mínimo: 0 (nunca negativo)
"""

from __future__ import annotations

from models.lead import Lead


class LeadScorer:
    """
    Calculadora de score de leads.
    Stateless — pode ser instanciada uma vez e reutilizada.
    """

    def score(self, lead: Lead) -> int:
        """
        Calcula e retorna o score do lead entre 0 e 100.

        O score é utilizado para priorizar leads no enriquecimento e
        na seleção de cadências.
        """
        points = 0

        if lead.linkedin_url:
            points += 20

        if lead.email_corporate:
            points += 25
            if lead.email_corporate_verified:
                points += 10
        elif lead.email_personal:
            # Tem e-mail mas apenas pessoal — pequena penalidade
            points -= 5

        if lead.company:
            points += 10

        if lead.website:
            points += 10

        if lead.phone:
            points += 5

        if lead.segment:
            points += 10

        if lead.city:
            points += 5

        return max(0, min(100, points))


# Singleton stateless
lead_scorer = LeadScorer()
