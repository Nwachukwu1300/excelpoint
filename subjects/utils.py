from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredExcelLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
)
from langchain.schema import Document
import PyPDF2
import os
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import mimetypes
from pydub import AudioSegment
import speech_recognition as sr
import tempfile
import psutil
import gc
import logging
from .llm_utils import generate_flashcards as llm_generate_flashcards
from .llm_utils import generate_quiz_questions as llm_generate_quiz_questions
from .llm_utils import answer_question as llm_answer_question

# Conditional import for transcription service
try:
    from .services.transcription_service import TranscriptionService
    TRANSCRIPTION_AVAILABLE = True
except ImportError:
    TranscriptionService = None
    TRANSCRIPTION_AVAILABLE = False

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean text by removing null characters and other problematic characters."""
    if not text:
        return ""
    
    # Remove null characters (0x00)
    text = text.replace('\x00', '')
    
    # Remove other control characters except newlines and tabs
    import re
    text = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file using PyPDF2."""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """Split text into chunks with overlap."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    return splitter.split_text(text)

class ContentProcessor:
    def __init__(self, batch_size: int = None, memory_threshold: float = 0.8):
        # Initialize the text splitter with optimal parameters
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Characters per chunk
            chunk_overlap=200,  # Overlap between chunks
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Initialize the sentence transformer for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize speech recognizer (legacy)
        self.recognizer = sr.Recognizer()
        
        # Initialize transcription service
        if TRANSCRIPTION_AVAILABLE:
            self.transcription_service = TranscriptionService()
        else:
            self.transcription_service = None
            logger.warning("Transcription service not available. Video/audio processing will not work.")
        
        # Initialize storage service for S3 file handling
        try:
            from .services.storage_factory import StorageFactory
            self.storage_service = StorageFactory.get_storage_service()
        except ImportError:
            self.storage_service = None
            logger.warning("Storage service not available. S3 file processing may not work.")
        
        # Batch processing configuration
        self.batch_size = batch_size or self._calculate_optimal_batch_size()
        self.memory_threshold = memory_threshold  # Memory usage threshold before triggering batch processing
        
        logger.info(f"ContentProcessor initialized with batch_size={self.batch_size}, memory_threshold={self.memory_threshold}")
    
    def _calculate_optimal_batch_size(self) -> int:
        """Calculate optimal batch size based on available memory and model requirements."""
        try:
            # Get available memory in GB
            available_memory_gb = psutil.virtual_memory().available / (1024**3)
            
            # Estimate memory usage per chunk (rough calculation)
            # all-MiniLM-L6-v2 produces 384-dimensional embeddings (float32 = 4 bytes each)
            # Plus overhead for text processing and model inference
            estimated_memory_per_chunk_mb = 2  # Conservative estimate
            
            # Calculate batch size to use ~50% of available memory for embedding generation
            target_memory_usage_gb = available_memory_gb * 0.5
            target_memory_usage_mb = target_memory_usage_gb * 1024
            
            batch_size = max(1, int(target_memory_usage_mb / estimated_memory_per_chunk_mb))
            
            # Cap batch size to reasonable limits
            batch_size = min(batch_size, 100)  # Max 100 chunks per batch
            batch_size = max(batch_size, 5)    # Min 5 chunks per batch
            
            logger.info(f"Calculated optimal batch size: {batch_size} (available memory: {available_memory_gb:.2f}GB)")
            return batch_size
            
        except Exception as e:
            logger.warning(f"Error calculating optimal batch size: {e}. Using default batch size of 20.")
            return 20
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            return psutil.virtual_memory().percent / 100.0
        except:
            return 0.5  # Default to 50% if can't determine
    
    def _should_use_batch_processing(self, num_chunks: int) -> bool:
        """Determine if batch processing should be used based on chunk count and memory."""
        memory_usage = self._get_memory_usage()
        
        # Use batch processing if:
        # 1. Memory usage is above threshold, OR
        # 2. Number of chunks exceeds 2x batch size
        should_batch = (memory_usage > self.memory_threshold) or (num_chunks > self.batch_size * 2)
        
        if should_batch:
            logger.info(f"Using batch processing: chunks={num_chunks}, memory={memory_usage:.1%}, threshold={self.memory_threshold:.1%}")
        
        return should_batch

    def get_file_type(self, file_path: str) -> str:
        """Determine the type of file based on its extension and mime type."""
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith('text/'):
                return 'TEXT'
            elif mime_type.startswith('audio/'):
                return 'AUDIO'
            elif mime_type.startswith('video/'):
                return 'VIDEO'
            elif mime_type == 'application/pdf':
                return 'PDF'
            elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                return 'DOC'
            elif mime_type in ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
                return 'PPT'
            elif mime_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
                return 'XLS'
            elif mime_type == 'text/html':
                return 'HTML'
            elif mime_type == 'text/markdown':
                return 'MD'
        
        # Fallback to extension-based detection for better audio/video support
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in ['.mp3', '.wav', '.m4a', '.aac', '.ogg']:
            return 'AUDIO'
        elif file_extension in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            return 'VIDEO'
        
        return 'UNKNOWN'

    def extract_text_from_audio(self, file_path: str) -> str:
        """Extract text from audio file using speech recognition."""
        try:
            # Convert audio to WAV format if needed
            audio = AudioSegment.from_file(file_path)
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                audio.export(temp_wav.name, format='wav')
                
                # Perform speech recognition
                with sr.AudioFile(temp_wav.name) as source:
                    audio_data = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio_data)
                
                # Clean up temporary file
                os.unlink(temp_wav.name)
                return text
                
        except Exception as e:
            raise Exception(f"Error processing audio file: {str(e)}")

    def _download_s3_file(self, s3_path: str) -> str:
        """Download S3 file to temporary location"""
        import tempfile
        import os
        
        if not self.storage_service:
            raise Exception("Storage service not available for S3 file download")
        
        # Extract bucket and key from S3 path
        if s3_path.startswith('s3://'):
            parts = s3_path[5:].split('/', 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ''
        else:
            # Handle URL format
            parts = s3_path.split('/')
            bucket = parts[2].split('.')[0]
            key = '/'.join(parts[3:])
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(key)[1])
        
        # Download from S3
        self.storage_service.s3_client.download_file(bucket, key, temp_file.name)
        
        return temp_file.name

    def process_file(self, file_path: str, use_batch_processing: bool = None) -> List[Dict[str, Any]]:
        """Process any type of file and return chunks with embeddings."""
        try:
            # Handle S3 files
            temp_file_path = None
            if file_path.startswith('s3://') or 's3.amazonaws.com' in file_path:
                logger.info(f"Processing S3 file: {file_path}")
                temp_file_path = self._download_s3_file(file_path)
                file_path = temp_file_path
            
            file_type = self.get_file_type(file_path)
            
            # Extract text based on file type
            if file_type == 'PDF':
                loader = PyPDFLoader(file_path)
                pages = loader.load()
                text = " ".join([page.page_content for page in pages])
            
            elif file_type == 'DOC':
                loader = UnstructuredWordDocumentLoader(file_path)
                text = loader.load()[0].page_content
            
            elif file_type == 'PPT':
                loader = UnstructuredPowerPointLoader(file_path)
                text = loader.load()[0].page_content
            
            elif file_type == 'XLS':
                loader = UnstructuredExcelLoader(file_path)
                text = loader.load()[0].page_content
            
            elif file_type == 'HTML':
                loader = UnstructuredHTMLLoader(file_path)
                text = loader.load()[0].page_content
            
            elif file_type == 'MD':
                loader = UnstructuredMarkdownLoader(file_path)
                text = loader.load()[0].page_content
            
            elif file_type == 'TEXT':
                loader = TextLoader(file_path)
                text = loader.load()[0].page_content
            
            elif file_type == 'AUDIO':
                # Use the new transcription service for audio files
                if self.transcription_service:
                    text = self.transcription_service.process_media_file(file_path, 'AUDIO')
                else:
                    raise Exception("Transcription service not available. Cannot process audio files.")
            
            elif file_type == 'VIDEO':
                # Use the new transcription service for video files
                if self.transcription_service:
                    text = self.transcription_service.process_media_file(file_path, 'VIDEO')
                else:
                    raise Exception("Transcription service not available. Cannot process video files.")
            
            else:
                raise Exception(f"Unsupported file type: {file_type}")
            
            # Clean the extracted text
            cleaned_text = clean_text(text)

            # Split into chunks
            chunks = self.text_splitter.split_text(cleaned_text)
            logger.info(f"Split file into {len(chunks)} chunks")
            
            # Determine if batch processing should be used
            if use_batch_processing is None:
                use_batch_processing = self._should_use_batch_processing(len(chunks))
            
            if use_batch_processing:
                result = self.process_chunks_in_batches(chunks)
            else:
                result = self.process_chunks_immediately(chunks)
            
            # Clean up temporary file if it was created
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.info(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_file_path}: {e}")
            
            return result
            
        except Exception as e:
            # Clean up temporary file on error
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            raise Exception(f"Error processing file: {str(e)}")
    
    def process_chunks_immediately(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """Process all chunks immediately (original behavior)."""
        logger.info(f"Processing {len(chunks)} chunks immediately")
        
        chunk_data = []
        for i, chunk in enumerate(chunks):
            # Clean the chunk content
            cleaned_chunk = clean_text(chunk)
            
            # Skip empty chunks
            if not cleaned_chunk:
                continue
                
            # Generate embedding
            embedding = self.model.encode(cleaned_chunk)
            
            chunk_data.append({
                'content': cleaned_chunk,
                'chunk_index': i,
                'embedding_vector': embedding.tolist()
            })
        
        return chunk_data
    
    def process_chunks_in_batches(self, chunks: List[str], progress_callback=None) -> List[Dict[str, Any]]:
        """Process chunks in batches to manage memory usage efficiently."""
        total_chunks = len(chunks)
        chunk_data = []
        
        logger.info(f"Processing {total_chunks} chunks in batches of {self.batch_size}")
        
        for batch_start in range(0, total_chunks, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_chunks)
            batch_chunks = chunks[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (total_chunks + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")
            
            # Check memory usage before processing batch
            memory_before = self._get_memory_usage()
            
            # Process batch
            batch_embeddings = self.model.encode(batch_chunks)
            
            # Convert to list format and add to results
            for i, (chunk, embedding) in enumerate(zip(batch_chunks, batch_embeddings)):
                # Clean the chunk content
                cleaned_chunk = clean_text(chunk)
                
                # Skip empty chunks
                if not cleaned_chunk:
                    continue
                    
                chunk_data.append({
                    'content': cleaned_chunk,
                    'chunk_index': batch_start + i,
                    'embedding_vector': embedding.tolist()
                })
            
            # Monitor memory usage
            memory_after = self._get_memory_usage()
            logger.debug(f"Batch {batch_num} completed. Memory: {memory_before:.1%} -> {memory_after:.1%}")
            
            # Call progress callback if provided
            if progress_callback:
                progress = batch_end / total_chunks
                progress_callback(progress, batch_num, total_batches)
            
            # Force garbage collection if memory usage is high
            if memory_after > 0.85:
                logger.info("High memory usage detected, forcing garbage collection")
                gc.collect()
                
                # Clear CUDA cache if using GPU
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        
        logger.info(f"Completed processing {total_chunks} chunks in {total_batches} batches")
        return chunk_data
    
    def process_file_with_progress(self, file_path: str, progress_callback=None) -> List[Dict[str, Any]]:
        """Process file with progress tracking callback."""
        return self.process_file(file_path, use_batch_processing=True)
    
    def find_relevant_chunks(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """Find the most relevant chunks for a given query using cosine similarity."""
        # Generate query embedding
        query_embedding = self.model.encode(query)
        
        # Calculate similarities
        similarities = []
        for chunk in chunks:
            chunk_embedding = np.array(chunk['embedding_vector'])
            similarity = np.dot(query_embedding, chunk_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
            )
            similarities.append((chunk, similarity))
        
        # Sort by similarity and return top k chunks
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in similarities[:top_k]]
    
    def generate_flashcards(self, chunks: List[Dict[str, Any]], num_cards: int = 5) -> List[Dict[str, str]]:
        """Generate flashcards from content chunks using LLM."""
        return llm_generate_flashcards(chunks, num_cards)
    
    def generate_quiz_questions(self, chunks: List[Dict[str, Any]], num_questions: int = 5) -> List[Dict[str, Any]]:
        """Generate quiz questions from content chunks using LLM."""
        return llm_generate_quiz_questions(chunks, num_questions)
    
    def answer_question(self, question: str, chunks: List[Dict[str, Any]]) -> str:
        """Answer a question using LLM and relevant content chunks."""
        relevant_chunks = self.find_relevant_chunks(question, chunks)
        return llm_answer_question(question, relevant_chunks) 