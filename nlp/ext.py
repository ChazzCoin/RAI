import re
import spacy
import nltk
from nltk import word_tokenize, sent_tokenize, FreqDist
from nltk.util import ngrams
from nltk.sentiment import SentimentIntensityAnalyzer

from rai.ingest.IngestModels import NLPAssistantModel

# Ensure necessary NLTK resources are available
nltk.download("punkt", quiet=True)
nltk.download("vader_lexicon", quiet=True)
import spacy.cli
spacy.cli.download("en_core_web_sm")

class NLPAssistant:
    """
    A robust class for text analysis using NLTK and spaCy.

    Methods:
      - tokenize: Returns a list of word tokens.
      - get_ngrams: Returns n-grams (default bigrams).
      - sentence_tokenize: Splits the text into sentences.
      - paragraphs: Splits the text into paragraphs.
      - pos_tags: Returns tokens with their part-of-speech tags.
      - named_entities: Extracts named entities from the text.
      - lemmatize: Returns the lemmas for tokens in the text.
      - dependency_parse: Provides dependency parsing information.
      - frequency_distribution: Computes the frequency distribution of tokens.
      - extract_urls: Extracts URLs found in the text.
      - sentiment_analysis: Analyzes sentiment using NLTK’s VADER.
      - summary: Provides a quick overview of text statistics.
    """

    def __init__(self):
        self.doc = None
        self.sentiment_analyzer = None
        self.nlp = None
        self.text = None

    @classmethod
    def analyze(cls, content:str) -> NLPAssistantModel:
        """
        Run the full analysis pipeline and return a populated TextAnalysisPipelineModel.
        """
        self = cls()
        self.load_text(content)
        tokens = self.tokenize()
        # Generate bigrams as joined strings for simplicity
        bigrams = [" ".join(bigram) for bigram in self.get_ngrams(2)]
        sentences = self.sentence_tokenize()
        paragraphs = self.paragraphs()
        pos_tags = self.pos_tags()
        named_entities = self.named_entities()
        lemmas = self.lemmatize()
        dependency_parse = self.dependency_parse()
        freq_dist = self.frequency_distribution()
        urls = self.extract_urls()
        sentiment = self.sentiment_analysis()
        summary = self.summary()

        return NLPAssistantModel(
            tokens=tokens,
            bigrams=bigrams,
            sentences=sentences,
            paragraphs=paragraphs,
            pos_tags=pos_tags,
            named_entities=named_entities,
            lemmas=lemmas,
            dependency_parse=dependency_parse,
            frequency_distribution=freq_dist,
            urls=urls,
            sentiment=sentiment,
            summary=summary
        )
    def load_text(self, text: str):
        self.text = text
        # Load the spaCy English model
        self.nlp = spacy.load("en_core_web_sm")
        self.doc = self.nlp(text)
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def tokenize(self):
        """Tokenize the text using NLTK's word_tokenize."""
        tokens = word_tokenize(self.text)
        return tokens

    def get_ngrams(self, n: int = 2):
        """Generate n-grams (default is bigrams) from the tokenized text."""
        tokens = self.tokenize()
        return list(ngrams(tokens, n))

    def sentence_tokenize(self):
        """Split the text into sentences using NLTK's sent_tokenize."""
        return sent_tokenize(self.text)

    def paragraphs(self):
        """
        Split the text into paragraphs.
        Assumes paragraphs are separated by two newlines.
        """
        return [p.strip() for p in self.text.split("\n\n") if p.strip()]

    def pos_tags(self):
        """
        Return a list of tuples where each tuple contains a token and its POS tag.
        Uses spaCy's tagging.
        """
        return [(token.text, token.pos_) for token in self.doc]

    def named_entities(self):
        """
        Extract named entities from the text using spaCy.
        Returns a list of tuples (entity text, entity label).
        """
        return [(ent.text, ent.label_) for ent in self.doc.ents]

    def lemmatize(self):
        """Return a list of lemmas for each token in the text using spaCy."""
        return [token.lemma_ for token in self.doc]

    def dependency_parse(self):
        """
        Return dependency parsing information.
        Each entry is a tuple: (token text, dependency relation, head token text).
        """
        return [(token.text, token.dep_, token.head.text) for token in self.doc]

    def frequency_distribution(self):
        """
        Compute the frequency distribution of tokens in the text using NLTK's FreqDist.
        Returns a dictionary of token frequencies.
        """
        tokens = self.tokenize()
        freq_dist = FreqDist(tokens)
        return dict(freq_dist)

    def extract_urls(self):
        """
        Extract URLs from the text using a regular expression.
        """
        url_pattern = r"https?://\S+"
        return re.findall(url_pattern, self.text)

    def sentiment_analysis(self):
        """
        Perform sentiment analysis on the text using NLTK's VADER.
        Returns a dictionary with sentiment scores.
        """
        scores = self.sentiment_analyzer.polarity_scores(self.text)
        return scores

    def summary(self):
        """
        Provide a summary of the text analysis including:
          - Sentence count
          - Token count
          - Named entity count
          - Average sentence length
        """
        sentences = self.sentence_tokenize()
        tokens = self.tokenize()
        ne = self.named_entities()
        avg_sentence_length = len(tokens) / len(sentences) if sentences else 0
        return {
            "sentence_count": len(sentences),
            "token_count": len(tokens),
            "named_entity_count": len(ne),
            "avg_sentence_length": avg_sentence_length
        }


# Example usage:
if __name__ == "__main__":
    sample_text = (
        "Apple Inc. is looking at buying U.K. startup for $1 billion. "
        "This move could revolutionize the tech market. "
        "Visit https://www.apple.com for more details.\n\n"
        "The company announced a new product line today."
    )

    # analyzer = TextAnalyzer(sample_text)
    # print("Tokens:", analyzer.tokenize())
    # print("Bigrams:", analyzer.get_ngrams(2))
    # print("Sentences:", analyzer.sentence_tokenize())
    # print("Paragraphs:", analyzer.paragraphs())
    # print("POS Tags:", analyzer.pos_tags())
    # print("Named Entities:", analyzer.named_entities())
    # print("Lemmas:", analyzer.lemmatize())
    # print("Dependency Parse:", analyzer.dependency_parse())
    # print("Frequency Distribution:", analyzer.frequency_distribution())
    # print("Extracted URLs:", analyzer.extract_urls())
    # print("Sentiment Analysis:", analyzer.sentiment_analysis())
    # print("Summary:", analyzer.summary())


