from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL
from app.utils.logger import get_logger

logger = get_logger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


def generate_ai_training_interpretation(
    activity: dict,
    ride_classification: str,
    weekly_context: dict | None,
    fallback_text: str,
) -> str:
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not configured. Using fallback interpretation.")
        return fallback_text

    weekly_distance = 0
    weekly_count = 0
    weekly_extra = ""

    if weekly_context:
        weekly_distance = weekly_context.get("current_distance", 0)
        weekly_count = weekly_context.get("current_count", 0)
        weekly_extra = weekly_context.get("extra", "")

    prompt = f"""
Você é um assistente de treino de ciclismo focado em atletas amadores.

Sua tarefa é gerar um comentário curto sobre um pedal, com uma interpretação simples e objetiva do esforço.

Use linguagem natural, clara e direta em português do Brasil.

Dados do pedal:
- Nome: {activity.get("name")}
- Tipo classificado: {ride_classification}
- Distância: {activity.get("distance_km")} km
- Tempo em movimento: {activity.get("moving_time_min")} minutos
- Elevação: {activity.get("elevation_gain_m")} m

Contexto recente:
- Pedais nos últimos 7 dias: {weekly_count}
- Distância nos últimos 7 dias: {weekly_distance} km
- Observação de carga: {weekly_extra}

Objetivo:
Interpretar o esforço do treino e seu impacto dentro do contexto recente.

Regras obrigatórias:
- Máximo de 2 frases
- Não usar números
- Não usar o nome do treino
- Não repetir dados já exibidos
- Não usar linguagem motivacional ou genérica
- Não explicar o que o atleta deve fazer
- Evitar frases vagas ou elogios sem justificativa

Estrutura:
- Primeira frase: interpretar o tipo de esforço e seu impacto
- Segunda frase: conectar com o contexto recente (carga, recuperação ou consistência)

Qualidade:
- Sempre conecte pelo menos dois fatores de forma concreta
- Evite conectores genéricos como "com a distância e o tempo"
- Prefira afirmações diretas e específicas
- Escreva como um treinador experiente, de forma objetiva

Ajustes finais de estilo:
- Evite termos fisiológicos como "frequência cardíaca", "musculatura"
- Evite expressões como "ideal para" ou "é essencial"
- Evite linguagem instrutiva
- Descreva o impacto do treino, não o que deve ser feito
"""

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
        )

        text = response.output_text.strip()

        if not text:
            logger.warning("OpenAI returned empty text. Using fallback interpretation.")
            return fallback_text

        logger.info("Generated AI training interpretation successfully.")
        return text

    except Exception as exc:
        logger.error("OpenAI generation failed: %s", exc)
        return fallback_text