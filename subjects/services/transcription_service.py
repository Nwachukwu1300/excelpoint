import os
import tempfile
import logging
from typing import Optional, Tuple
from pydub import AudioSegment
import whisper
from django.conf import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    Service for transcribing video and audio files using OpenAI Whisper.
    Handles audio extraction from video files and transcription of audio content.
    """
    
    def __init__(self):
        """Initialize the transcription service with Whisper model."""
        try:
            # Load Whisper model (will download on first use)
            self.model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def extract_audio_from_video(self, video_path: str) -> str:
        """
        Extract audio track from video file.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the extracted audio file
        """
        try:
            # Create temporary file for audio
            temp_audio = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio_path = temp_audio.name
            temp_audio.close()
            
            # Load video and extract audio
            video = AudioSegment.from_file(video_path)
            
            # Export audio as WAV
            video.export(temp_audio_path, format="wav")
            
            logger.info(f"Audio extracted from video: {video_path} -> {temp_audio_path}")
            return temp_audio_path
            
        except Exception as e:
            logger.error(f"Error extracting audio from video {video_path}: {e}")
            raise Exception(f"Failed to extract audio from video: {str(e)}")
    
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to the audio file
            language: Language code (optional, Whisper will auto-detect if None)
            
        Returns:
            Transcribed text
        """
        try:
            logger.info(f"Starting transcription of: {audio_path}")
            
            # Transcribe using Whisper
            if language:
                result = self.model.transcribe(audio_path, language=language)
            else:
                result = self.model.transcribe(audio_path)
            
            transcript = result["text"].strip()
            
            logger.info(f"Transcription completed. Length: {len(transcript)} characters")
            return transcript
            
        except Exception as e:
            logger.error(f"Error transcribing audio {audio_path}: {e}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    def transcribe_video(self, video_path: str, language: Optional[str] = None) -> str:
        """
        Transcribe video file by extracting audio and transcribing it.
        
        Args:
            video_path: Path to the video file
            language: Language code (optional)
            
        Returns:
            Transcribed text
        """
        temp_audio_path = None
        try:
            # Extract audio from video
            temp_audio_path = self.extract_audio_from_video(video_path)
            
            # Transcribe the extracted audio
            transcript = self.transcribe_audio(temp_audio_path, language)
            
            return transcript
            
        finally:
            # Clean up temporary audio file
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                    logger.debug(f"Cleaned up temporary audio file: {temp_audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary audio file: {e}")
    
    def process_media_file(self, file_path: str, file_type: str, language: Optional[str] = None) -> str:
        """
        Process media file (video or audio) and return transcript.
        
        Args:
            file_path: Path to the media file
            file_type: Type of file ('VIDEO' or 'AUDIO')
            language: Language code (optional)
            
        Returns:
            Transcribed text
        """
        try:
            if file_type == 'VIDEO':
                return self.transcribe_video(file_path, language)
            elif file_type == 'AUDIO':
                return self.transcribe_audio(file_path, language)
            else:
                raise ValueError(f"Unsupported file type for transcription: {file_type}")
                
        except Exception as e:
            logger.error(f"Error processing media file {file_path}: {e}")
            raise
    
    def get_transcription_status(self, file_path: str) -> dict:
        """
        Get status information about transcription process.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Dictionary with status information
        """
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    'status': 'error',
                    'message': 'File not found',
                    'progress': 0
                }
            
            # Get file size for progress estimation
            file_size = os.path.getsize(file_path)
            
            return {
                'status': 'ready',
                'file_size': file_size,
                'progress': 0,
                'message': 'File ready for transcription'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'progress': 0
            } 