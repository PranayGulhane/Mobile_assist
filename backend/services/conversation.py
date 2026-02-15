CREDIT_CARD_KNOWLEDGE = {
    "bill_generation": (
        "Your credit card bill is generated on the 1st of every month. "
        "The billing cycle runs from the 1st to the last day of each month."
    ),
    "payment_deduction": (
        "Payment is automatically deducted 15 days after bill generation, "
        "on the 16th of each month from your registered bank account."
    ),
    "outstanding_balance": (
        "Your current outstanding balance can be checked in your monthly statement. "
        "For the most accurate balance, please check your latest statement or "
        "contact your bank directly."
    ),
    "due_date": (
        "Your payment due date is the 16th of every month. "
        "A grace period of 3 days is available until the 19th without late fees."
    ),
    "double_deduction": (
        "We understand your concern about a double deduction. This has been noted "
        "and will be investigated. A refund will be processed within 5-7 business "
        "days if confirmed."
    ),
    "incorrect_billing": (
        "We take incorrect billing seriously. Your complaint has been registered "
        "and our billing team will review your account within 24 hours."
    ),
    "unauthorized_charge": (
        "An unauthorized charge is a serious matter. We will immediately flag your "
        "account for review and our fraud team will investigate within 24 hours."
    ),
    "missing_refund": (
        "Refunds typically take 7-10 business days to process. If it has been "
        "longer, your case will be escalated for immediate review."
    ),
}

COMPLAINT_PATTERNS = {
    "double_deduction": ["double", "twice", "charged twice"],
    "incorrect_billing": ["incorrect", "wrong", "error", "mistake"],
    "unauthorized_charge": ["unauthorized", "fraud"],
    "missing_refund": ["refund", "not received", "missing refund"],
}

INFORMATIONAL_PATTERNS = {
    "bill_generation": {
        "required": ["bill"],
        "any_of": ["generat", "when", "date"],
    },
    "payment_deduction": {
        "required": ["payment"],
        "any_of": ["deduct", "when"],
    },
    "outstanding_balance": {
        "required": [],
        "any_of": ["balance", "outstanding", "owe"],
    },
    "due_date": {
        "required": ["due"],
        "any_of": ["date", "when"],
    },
}

GOODBYE_EXACT = {
    "no", "nope", "nah", "bye", "goodbye", "good bye",
    "thanks", "thank you", "thankyou", "done",
}

GOODBYE_PHRASES = [
    "no thanks", "no thank you", "nothing", "that's all",
    "thats all", "that is all", "i'm good", "im good", "all good",
    "nothing else", "no more", "i'm done", "im done",
    "not right now", "maybe later", "that's it", "thats it",
    "have a good day", "take care", "see you", "no questions",
    "nothing more", "all set", "we're good", "i am good",
    "no i don't", "no i dont", "okay thanks", "ok thanks",
    "okay bye", "ok bye", "no that's it", "no thats it",
    "that will be all", "i think that's all", "no more questions",
]

FAREWELL_RESPONSE = (
    "It was great helping you today! If you ever have more questions "
    "about your credit card, don't hesitate to reach out. "
    "Have a wonderful day. Goodbye!"
)


def classify_intent(message: str) -> tuple[str, str]:
    message_lower = message.lower().strip()

    if _is_goodbye(message_lower):
        return "farewell", "farewell"

    for topic, keywords in COMPLAINT_PATTERNS.items():
        if any(kw in message_lower for kw in keywords):
            return "complaint", topic

    for topic, patterns in INFORMATIONAL_PATTERNS.items():
        required_match = all(kw in message_lower for kw in patterns["required"])
        any_match = any(kw in message_lower for kw in patterns["any_of"])
        if required_match and any_match:
            return "informational", topic

    return "informational", "general"


def _is_goodbye(message_lower: str) -> bool:
    cleaned = message_lower.rstrip(".!?,").strip()

    if cleaned in GOODBYE_EXACT:
        return True

    if len(cleaned.split()) > 8:
        return False

    for phrase in GOODBYE_PHRASES:
        if phrase in cleaned:
            return True

    return False


def get_knowledge_response(topic: str) -> str:
    return CREDIT_CARD_KNOWLEDGE.get(
        topic,
        "I'd be happy to help you with that. Could you provide more details "
        "about your credit card query so I can assist you better?",
    )


ESCALATION_RESPONSE = (
    "I understand your frustration, and I sincerely apologize for the inconvenience. "
    "I'm arranging for a customer care executive to review this and assist you. "
    "They will connect with you within 30 minutes."
)
