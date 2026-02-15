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


def classify_intent(message: str) -> tuple[str, str]:
    message_lower = message.lower()

    for topic, keywords in COMPLAINT_PATTERNS.items():
        if any(kw in message_lower for kw in keywords):
            return "complaint", topic

    for topic, patterns in INFORMATIONAL_PATTERNS.items():
        required_match = all(kw in message_lower for kw in patterns["required"])
        any_match = any(kw in message_lower for kw in patterns["any_of"])
        if required_match and any_match:
            return "informational", topic

    return "informational", "bill_generation"


def get_knowledge_response(topic: str) -> str:
    return CREDIT_CARD_KNOWLEDGE.get(
        topic,
        "I'd be happy to help you with that. Could you provide more details about your query?",
    )


ESCALATION_RESPONSE = (
    "I understand your frustration, and I sincerely apologize for the inconvenience. "
    "A customer care executive will connect with you within 30 minutes to resolve "
    "this personally. Your concern has been escalated to our priority queue."
)
