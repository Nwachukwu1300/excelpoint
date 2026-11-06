"""XP's spoken replies. XP_VOICE picks the provider; to add one, write a function and add it to PROVIDERS."""

from django.conf import settings
from openai import OpenAI


def _browser(text):
    return None  # the app speaks the reply with the device's own voice (speechSynthesis), for free


def _openai(text):
    response = OpenAI(api_key=settings.OPENAI_API_KEY).audio.speech.create(
        model=settings.XP_VOICE_MODEL, voice=settings.XP_VOICE_NAME, input=text, response_format='mp3')
    return response.content


PROVIDERS = {'browser': _browser, 'openai': _openai}


def provider():
    return settings.XP_VOICE if settings.XP_VOICE in PROVIDERS else 'browser'


def speak(text):
    """MP3 bytes for the reply, or None when the browser speaks it."""
    return PROVIDERS[provider()](text)
