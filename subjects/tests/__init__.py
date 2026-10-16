from subjects.models import EMBEDDING_DIMENSIONS


def vec(*values):
    """Pad a short test vector to the stored dimension; zero padding keeps cosine similarity unchanged."""
    return [float(v) for v in values] + [0.0] * (EMBEDDING_DIMENSIONS - len(values))
