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
from .llm_utils import generate_flashcards as llm_generate_flashcards
from .llm_utils import generate_quiz_questions as llm_generate_quiz_questions
from .llm_utils import answer_question as llm_answer_question

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
    def __init__(self):
        # Initialize the text splitter with optimal parameters
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Characters per chunk
            chunk_overlap=200,  # Overlap between chunks
            length_function=len,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Initialize the sentence transformer for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
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

    def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process any type of file and return chunks with embeddings."""
        try:
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
                text = self.extract_text_from_audio(file_path)
            
            elif file_type == 'VIDEO':
                # For video, we'll assume the transcript is already extracted
                # and saved as a text file with the same name
                transcript_path = os.path.splitext(file_path)[0] + '.txt'
                if os.path.exists(transcript_path):
                    with open(transcript_path, 'r') as f:
                        text = f.read()
                else:
                    raise Exception("Video transcript not found")
            
            else:
                raise Exception(f"Unsupported file type: {file_type}")
            
            # Split into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Generate embeddings for each chunk
            chunk_data = []
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.model.encode(chunk)
                
                chunk_data.append({
                    'content': chunk,
                    'chunk_index': i,
                    'embedding_vector': embedding.tolist()
                })
            
            return chunk_data
            
        except Exception as e:
            raise Exception(f"Error processing file: {str(e)}")
    
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