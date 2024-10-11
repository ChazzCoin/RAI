from nlp import Re


class ContextHelper(object):
    financial = [
        'fee', 'fees', 'cost', 'costs', 'payment', 'payments', 'money', 'dues',
        'price', 'prices', 'rate', 'rates', 'expense', 'expenses', 'charge', 'charges',
        'deposit', 'deposits', 'tuition', 'registration fee', 'annual fee',
        'membership fee', 'subscription', 'subscription fee', 'league fee',
        'tournament fee', 'uniform fee', 'equipment fee', 'travel expense',
        'camp fee', 'clinic fee', 'fundraising', 'fundraising goal',
        'late fee', 'penalty', 'scholarship', 'financial aid', 'sponsorship',
        'donation', 'contribution', 'budget', 'billing', 'invoice', 'installment',
        'installment plan', 'discount', 'early bird discount', 'refund', 'rebate',
        'overdue payment', 'credit card payment', 'check payment', 'cash payment',
        'payment plan', 'automatic payment', 'ACH payment', 'wire transfer',
        'e-payment', 'online payment', 'registration cost', 'season fee',
        'monthly fee', 'quarterly fee', 'yearly fee', 'weekly fee',
        'one-time fee', 'recurring fee', 'cancellation fee', 'processing fee',
        'administrative fee', 'handling fee', 'service charge', 'service fee',
        'transaction fee', 'convenience fee', 'program fee', 'league dues',
        'team fee', 'participation fee', 'sports fee', 'activity fee',
        'tuition fee', 'entry fee', 'registration deposit', 'family discount',
        'multi-child discount', 'season pass', 'event fee', 'booking fee',
        'reservation fee'
    ]

    @staticmethod
    def is_in_context(text:str, context_list:list) -> bool:
        return Re.contains_any(context_list, text)

    def is_financial_context(self, text:str) -> bool:
        return Re.contains_any(self.financial, text)


class SoccerContext:
    system_prompt: str = ""
    financial_context: list = ['fee', 'fees', 'cost', 'payment', 'money', 'dues']

    def __init__(self):
        pass