"""
prompts.py — all prompt engineering for ModelSabha in one place.

The debate has three stages, each with its own prompt:

  Stage 1  OPENING   — each model answers the question independently.
  Stage 2  CRITIQUE  — each model reads the OTHER models' answers and
                       says where they agree, disagree, or spot mistakes.
  Stage 3  VERDICT   — a separate "judge" model reads everything and
                       returns a strict-JSON ruling with a consensus score.

Keeping prompts here (not buried inside route handlers) makes them easy
to show judges and easy to tune without touching application logic.
"""

OPENING_SYSTEM = """You are one member of a small council of AI models called a Sabha.
A person has brought a real question or decision to the council.

Give YOUR independent answer. Rules:
- Be direct: lead with your recommendation or answer in the first sentence.
- Then give your 2-3 strongest reasons.
- If the question has real uncertainty, say what it depends on.
- Maximum 150 words. No headings, no bullet lists — write naturally."""


def opening_messages(question: str) -> list[dict]:
    return [
        {"role": "system", "content": OPENING_SYSTEM},
        {"role": "user", "content": question},
    ]


CRITIQUE_SYSTEM = """You are a member of an AI council reviewing your peers' answers
to the same question you just answered.

You will see the other members' answers (not your own). Your job:
- Point out the single most important thing you DISAGREE with or think is
  wrong/missing, and say why — be specific, quote the claim you dispute.
- Also name one thing a peer got right that you had missed, if any.
- If you now want to revise your own position, say so honestly.
- Maximum 120 words. Plain prose."""


def critique_messages(question: str, own_answer: str, peer_answers: list[dict]) -> list[dict]:
    peers_text = "\n\n".join(
        f"--- Answer from {peer['model']} ---\n{peer['content']}"
        for peer in peer_answers
    )
    user = (
        f"The question was:\n{question}\n\n"
        f"Your earlier answer was:\n{own_answer}\n\n"
        f"Here are your peers' answers:\n\n{peers_text}"
    )
    return [
        {"role": "system", "content": CRITIQUE_SYSTEM},
        {"role": "user", "content": user},
    ]


VERDICT_SYSTEM = """You are the presiding judge of an AI council (a Sabha).
Several AI models answered a question, then critiqued each other.
Your job is to deliver a final, useful verdict for the human.

Respond with ONLY a JSON object — no markdown fences, no extra text — using
exactly this schema:
{
  "verdict": "The final recommended answer, 2-4 sentences, actionable.",
  "one_liner": "The verdict compressed to one punchy sentence.",
  "consensus_score": 0-100 integer (100 = models fully agree, 0 = total conflict),
  "agreements": ["short point every model agreed on", ...],
  "disagreements": ["short description of a real conflict between models", ...],
  "strongest_voice": "the model id whose reasoning was most convincing",
  "caution": "one sentence on what the human should still verify themselves"
}

Be honest: if the models genuinely conflict, give a LOW consensus_score and
say so in the verdict rather than papering over the disagreement."""


def verdict_messages(question: str, answers: list[dict], critiques: list[dict]) -> list[dict]:
    answers_text = "\n\n".join(
        f"--- {a['model']} answered ---\n{a['content']}" for a in answers
    )
    critiques_text = "\n\n".join(
        f"--- {c['model']} critiqued the others ---\n{c['content']}" for c in critiques
    )
    user = (
        f"Question brought to the council:\n{question}\n\n"
        f"ROUND 1 — OPENING ANSWERS:\n{answers_text}\n\n"
        f"ROUND 2 — CROSS-EXAMINATION:\n{critiques_text}\n\n"
        f"Deliver your JSON verdict now."
    )
    return [
        {"role": "system", "content": VERDICT_SYSTEM},
        {"role": "user", "content": user},
    ]
