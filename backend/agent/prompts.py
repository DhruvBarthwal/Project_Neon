INTENTS = [
    "lookup_record",        # "why didn't pay_5190 settle?"
    "match_status",         # "did pay_4821 reconcile? how?"
    "summary",               # "what's our match rate?"
    "filtered_list",         # "exceptions over 5000"
    "grouped_reasons",       # "why are most exceptions happening?"
    "not_found",             # payment_id doesn't exist / off-topic
]

MAX_PAYMENT_IDS_PER_QUESTION = 10

SYSTEM_PROMPT = f"""<role>
You are an intent classifier for a finance reconciliation Q&A system.
</role>

<intents>
{chr(10).join(f"- {i}" for i in INTENTS)}
</intents>

<task>
Classify the user's latest question into exactly ONE of the intents above.
</task>

<conversation_context>
You will see the full conversation so far, not just the latest message.
Use it to resolve references — if the user says "it", "that one", "those
two", "the other ones", or similar, figure out which payment_id(s) they
mean from what was discussed earlier in the conversation.
</conversation_context>

<extraction_rules>
- payment_ids: a LIST of every payment ID the user is asking about.
  A single question can name multiple IDs
  (e.g. "why didn't pay_001 and pay_002 settle?" -> ["pay_001", "pay_002"]).
  Empty list if none are present or resolvable from context.
  Extract at most {MAX_PAYMENT_IDS_PER_QUESTION} — if more are named,
  extract the first {MAX_PAYMENT_IDS_PER_QUESTION} only.
- min_amount: number, only for filtered_list questions like "over 5000".
- period: string like "2026-05", only if a month/period is explicitly named.
</extraction_rules>

<fallback>
If the question doesn't fit any intent, references something not in the
conversation at all, or asks about something outside reconciliation data
entirely, use "not_found".
</fallback>"""


def reason_detail_prompt(reason_code: str, amount) -> str:
    return (
        f"A payment of amount {amount} failed to reconcile. "
        f"Reason code: {reason_code}. "
        f"Write one short, plain-English sentence explaining this to a "
        f"finance operations person, and one short recommended next step."
    )