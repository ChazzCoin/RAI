


"""
CONTEXT ANALYZER
"""
from F import LIST

from nlp.Categorizer import Topics


def analyze_context(request_in: str, default:str):
    r = default

    def analyzer(user_input:str):
        results = Topics.RUN_MAIN_CATEGORIZER(user_input)
        return results

    try:
        user_context = analyzer(request_in)
        if user_context:
            r = LIST.get(0, user_context, default)
        print(r)
    except Exception as e:
        print(e)

    return r

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
    development_soccer = [
        'development', 'training', 'learn', 'learning', 'drills', 'skills', 'practice', 'coaching', 'growth', 'improvement', 'progress', 'academy', 'soccer drills', 'technique', 'tactics', 'soccer skills'
    ]
    schedule = [
        'schedule', 'games', 'practice', 'time', 'date', 'event', 'where', 'when',
        'what time', 'tournament', 'match', 'game day', 'fixture', 'training time', 'venue', 'calendar', 'session', 'appointment', 'meeting', 'arrangement', 'agenda'
    ]
    onboarding = [
        'onboarding', 'employee', 'training', 'new', 'help', 'setup', 'orientation', 'introduction', 'induction', 'welcome', 'getting started', 'guide', 'process', 'procedure', 'registration', 'enrollment', 'initiation'
    ]

    @staticmethod
    def is_in_context(text: str, context_list: list) -> bool:
        return any(word in text for word in context_list)

    def is_financial_context(self, text: str) -> bool:
        return self.is_in_context(text, self.financial)

    def count_word_occurrences(self, text: str) -> dict:
        words = text.split()
        word_count = {}
        for word in words:
            word = word.lower().strip('.,!?()[]{}"')  # Basic cleanup
            word_count[word] = word_count.get(word, 0) + 1
        return word_count

    def calculate_context_score(self, text: str, context_list: list) -> int:
        word_count = self.count_word_occurrences(text)
        score = 0
        for word in context_list:
            score += word_count.get(word, 0)
        return score

    def get_top_two_contexts(self, text: str) -> list:
        context_scores = {
            'financial': self.calculate_context_score(text, self.financial),
            'development_soccer': self.calculate_context_score(text, self.development_soccer),
            'schedule': self.calculate_context_score(text, self.schedule),
            'onboarding': self.calculate_context_score(text, self.onboarding)
        }
        sorted_contexts = sorted(context_scores.items(), key=lambda x: x[1], reverse=True)
        return [context[0] for context in sorted_contexts[:2]]