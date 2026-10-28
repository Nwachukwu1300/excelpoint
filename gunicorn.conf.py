"""Gunicorn settings (read automatically from the working directory)."""

bind = '0.0.0.0:8000'
workers = 2
threads = 8  # threaded workers, so a streaming chat answer doesn't hold a whole worker
timeout = 120  # a reasoning answer can take tens of seconds


def post_worker_init(worker):
    # Load the embedding model now, not on the first question (it takes seconds)
    from subjects.utils import load_embedding_model
    load_embedding_model()
