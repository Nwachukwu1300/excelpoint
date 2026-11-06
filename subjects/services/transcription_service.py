"""Audio and video to text with OpenAI's transcription API (gpt-transcribe).

The API takes files up to 25 MB, and not MOV or AVI. So ffmpeg first turns any upload (up to 100 MB)
into small mono MP3 chunks, and each chunk is transcribed in turn.
"""

import glob
import shutil
import subprocess
import tempfile

from django.conf import settings
from openai import OpenAI

MODEL = 'gpt-transcribe'
CHUNK_SECONDS = 20 * 60  # 20 minutes of 32 kbps mono MP3 is about 5 MB, well under the 25 MB limit
MAX_SECONDS = 3 * 60 * 60  # caps the cost of one upload (about $0.80); 100 MB of low-bitrate audio could be 20+ hours


def transcription_available():
    return bool(settings.OPENAI_API_KEY) and shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None


def transcribe(path: str, model: str = MODEL) -> str:
    from ..utils import UnreadableFile  # utils imports this module

    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                           capture_output=True, text=True, timeout=60)
    try:
        seconds = float(probe.stdout.strip())
    except ValueError:
        raise UnreadableFile("We couldn't find any sound in this file. Check that it plays, then upload it again.")
    if seconds > MAX_SECONDS:
        raise UnreadableFile(f'This recording is {seconds / 3600:.1f} hours long. Recordings can be up to 3 hours; '
                             'split it into parts and upload each one.')

    with tempfile.TemporaryDirectory() as folder:
        # shortcut: fixed 20-minute cuts can split a sentence; switch to silence-based cuts if accuracy suffers
        result = subprocess.run(
            ['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', path, '-t', str(MAX_SECONDS), '-vn', '-ac', '1', '-ar', '16000', '-b:a', '32k',
             '-f', 'segment', '-segment_time', str(CHUNK_SECONDS), f'{folder}/part%03d.mp3'],
            capture_output=True, text=True, timeout=30 * 60,
        )
        chunks = sorted(glob.glob(f'{folder}/part*.mp3'))
        if result.returncode != 0 or not chunks:
            raise UnreadableFile("We couldn't find any sound in this file. Check that it plays, then upload it again.")
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        texts = []
        for chunk in chunks:
            with open(chunk, 'rb') as audio:
                texts.append(client.audio.transcriptions.create(model=model, file=audio).text.strip())
    text = '\n\n'.join(t for t in texts if t)
    if not text:
        raise UnreadableFile('No speech found in this recording.')
    return text
