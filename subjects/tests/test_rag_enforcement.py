"""
Comprehensive test suite for RAG-based XP Bot material-only enforcement.

This test suite ensures that XP ONLY responds with information from uploaded materials
and never leaks general knowledge or external information.
"""

import unittest
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from subjects.models import Subject, SubjectMaterial, ContentChunk
from subjects.services.rag_service import RAGService
from subjects.services.vector_search import VectorSearchService
import logging

User = get_user_model()

class RAGEnforcementTestCase(TestCase):
    """Test suite for RAG material-only enforcement"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test subjects
        self.comp_sci_subject = Subject.objects.create(
            user=self.user,
            name='Computer Science'
        )
        
        self.math_subject = Subject.objects.create(
            user=self.user,
            name='Mathematics'
        )
        
        # Initialize RAG service
        self.rag_service = RAGService()
        
        # Mock successful chunk retrieval for positive tests
        self.mock_relevant_chunks = [
            {
                'content': 'SQL (Structured Query Language) is used to manage databases. DDL stands for Data Definition Language.',
                'material_name': 'database_notes.pdf',
                'similarity_score': 0.8
            }
        ]
        
    def test_general_knowledge_queries_blocked(self):
        """Test that general knowledge queries are blocked"""
        general_knowledge_queries = [
            "What is the capital of France?",
            "Who invented the telephone?", 
            "What year did World War II end?",
            "How many planets are in our solar system?",
            "What is the speed of light?",
            "Who wrote Romeo and Juliet?",
            "What is the largest ocean on Earth?",
            "When was the Declaration of Independence signed?",
            "What is the chemical symbol for gold?",
            "Who painted the Mona Lisa?"
        ]
        
        for query in general_knowledge_queries:
            with self.subTest(query=query):
                # Mock no relevant chunks found
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=[]):
                    result = self.rag_service.generate_response(
                        query=query,
                        subject_id=self.comp_sci_subject.id,
                        chat_history=[],
                        user_id=self.user.id
                    )
                    
                    # Should return subject-specific fallback
                    self.assertIn('Computer Science', result['response'])
                    self.assertIn('materials', result['response'])
                    self.assertFalse(result['context_used'])
    
    def test_academic_general_knowledge_blocked(self):
        """Test that academic general knowledge is blocked"""
        academic_queries = [
            "What is machine learning?",
            "Explain object-oriented programming",
            "What are the principles of database normalization?",
            "How does TCP/IP work?",
            "What is Big O notation?",
            "Explain the OSI model",
            "What is recursion in programming?",
            "How do hash tables work?",
            "What is the difference between SQL and NoSQL?",
            "Explain artificial intelligence"
        ]
        
        for query in academic_queries:
            with self.subTest(query=query):
                # Mock no relevant chunks found (simulating missing material)
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=[]):
                    result = self.rag_service.generate_response(
                        query=query,
                        subject_id=self.comp_sci_subject.id,
                        chat_history=[],
                        user_id=self.user.id
                    )
                    
                    # Should return fallback, not general knowledge
                    self.assertIn('Computer Science', result['response'])
                    self.assertFalse(result['context_used'])
                    
                    # Check that response doesn't contain general knowledge indicators
                    response_lower = result['response'].lower()
                    forbidden_phrases = [
                        'generally speaking', 'typically', 'usually', 'commonly',
                        'it is well known', 'studies show', 'research indicates'
                    ]
                    
                    for phrase in forbidden_phrases:
                        self.assertNotIn(phrase, response_lower)
    
    def test_material_based_responses_allowed(self):
        """Test that material-based responses are properly generated"""
        material_queries = [
            "What is DDL?",
            "How do you create SQL tables?", 
            "What does SQL stand for?"
        ]
        
        for query in material_queries:
            with self.subTest(query=query):
                # Mock relevant chunks found
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=self.mock_relevant_chunks):
                    with patch.object(self.rag_service, '_generate_llm_response') as mock_llm:
                        mock_llm.return_value = {
                            'content': 'Based on your materials, DDL stands for Data Definition Language and is used to define database structure.',
                            'usage': {'total_tokens': 50}
                        }
                        
                        result = self.rag_service.generate_response(
                            query=query,
                            subject_id=self.comp_sci_subject.id,
                            chat_history=[],
                            user_id=self.user.id
                        )
                        
                        # Should use context and provide material-based response
                        self.assertTrue(result['context_used'])
                        self.assertIn('DDL', result['response'])
                        self.assertNotIn('Computer Science materials', result['response'])  # Not fallback
    
    def test_cross_subject_contamination_prevented(self):
        """Test that responses don't leak information from other subjects"""
        # Query about math in computer science subject
        math_queries = [
            "What is calculus?",
            "How do you solve quadratic equations?",
            "What is linear algebra?"
        ]
        
        for query in math_queries:
            with self.subTest(query=query):
                # Mock no relevant chunks in comp sci subject
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=[]):
                    result = self.rag_service.generate_response(
                        query=query,
                        subject_id=self.comp_sci_subject.id,  # Computer Science subject
                        chat_history=[],
                        user_id=self.user.id
                    )
                    
                    # Should return comp sci specific fallback, not math knowledge
                    self.assertIn('Computer Science', result['response'])
                    self.assertFalse(result['context_used'])
    
    def test_response_validation_catches_leakage(self):
        """Test that response validation catches potential general knowledge leakage"""
        # Test general knowledge indicators detection
        test_cases = [
            ("Generally speaking, databases are important.", True),
            ("According to studies, SQL is widely used.", True), 
            ("Based on your materials, DDL creates tables.", False),
            ("From the uploaded document, SQL stands for Structured Query Language.", False),
            ("Everyone knows that databases store data.", True),
            ("It's obvious that programming requires logic.", True)
        ]
        
        for response_text, should_be_blocked in test_cases:
            with self.subTest(response=response_text):
                contains_indicators = self.rag_service._contains_general_knowledge_indicators(response_text)
                self.assertEqual(contains_indicators, should_be_blocked)
    
    def test_prohibited_patterns_detection(self):
        """Test that prohibited patterns are properly detected"""
        test_cases = [
            ("According to Wikipedia, SQL is a language.", True),
            ("I learned from my training that databases are important.", True),
            ("As an AI assistant, I can help you.", True),
            ("Currently, databases are widely used.", True),
            ("Based on the provided materials, DDL is used for schema definition.", False),
            ("The document states that SQL creates tables.", False)
        ]
        
        for response_text, should_be_blocked in test_cases:
            with self.subTest(response=response_text):
                contains_prohibited = self.rag_service._contains_prohibited_patterns(response_text)
                self.assertEqual(contains_prohibited, should_be_blocked)
    
    def test_content_grounding_validation(self):
        """Test that content grounding validation works correctly"""
        context = "SQL stands for Structured Query Language. DDL is Data Definition Language used to create and modify database structures."
        
        test_cases = [
            ("SQL stands for Structured Query Language.", True),  # Well grounded
            ("DDL creates database tables and structures.", True),  # Well grounded
            ("Python is a programming language used for web development.", False),  # Not grounded
            ("Machine learning algorithms require large datasets.", False)  # Not grounded
        ]
        
        for response_text, should_pass in test_cases:
            with self.subTest(response=response_text):
                is_grounded = self.rag_service._is_response_grounded_in_context(response_text, context)
                self.assertEqual(is_grounded, should_pass)
    
    def test_subject_specific_fallback_generation(self):
        """Test that subject-specific fallback messages are generated correctly"""
        # Test with different subject names
        test_subjects = [
            ("Computer Science", "Computer Science"),
            ("Mathematics", "Mathematics"), 
            ("Data Science", "Data Science")
        ]
        
        for subject_name, expected_name in test_subjects:
            with self.subTest(subject=subject_name):
                fallback = self.rag_service._get_subject_specific_fallback(subject_name)
                
                # Should contain subject name multiple times
                self.assertIn(expected_name, fallback)
                # Should provide helpful guidance
                self.assertIn('materials', fallback)
                self.assertIn('documents', fallback)
                self.assertIn('uploading', fallback)
    
    def test_edge_cases_with_minimal_context(self):
        """Test behavior with minimal or poor quality context"""
        edge_cases = [
            "",  # Empty context
            "   ",  # Whitespace only
            "a b c",  # Minimal content
            "The document contains information."  # Vague content
        ]
        
        for context in edge_cases:
            with self.subTest(context=repr(context)):
                # Mock minimal context
                minimal_chunks = [{'content': context, 'material_name': 'test.pdf', 'similarity_score': 0.4}] if context.strip() else []
                
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=minimal_chunks):
                    result = self.rag_service.generate_response(
                        query="What is database normalization?",
                        subject_id=self.comp_sci_subject.id,
                        chat_history=[],
                        user_id=self.user.id
                    )
                    
                    # Should return fallback for insufficient context
                    self.assertIn('Computer Science', result['response'])
    
    def test_various_similarity_thresholds(self):
        """Test system behavior with different similarity thresholds"""
        # Create chunks with different similarity scores
        test_chunks = [
            {'content': 'SQL creates database tables', 'material_name': 'test.pdf', 'similarity_score': 0.8},
            {'content': 'Database management systems', 'material_name': 'test.pdf', 'similarity_score': 0.4},
            {'content': 'Data storage concepts', 'material_name': 'test.pdf', 'similarity_score': 0.3}
        ]
        
        # Test with different threshold configurations
        thresholds = [0.3, 0.45, 0.7]
        
        for threshold in thresholds:
            with self.subTest(threshold=threshold):
                # Temporarily modify threshold
                original_threshold = self.rag_service.search_threshold
                self.rag_service.search_threshold = threshold
                
                try:
                    # Filter chunks based on threshold
                    filtered_chunks = [chunk for chunk in test_chunks if chunk['similarity_score'] >= threshold]
                    
                    with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=filtered_chunks):
                        result = self.rag_service.generate_response(
                            query="What is SQL?",
                            subject_id=self.comp_sci_subject.id,
                            chat_history=[],
                            user_id=self.user.id
                        )
                        
                        # Verify appropriate response based on available chunks
                        if filtered_chunks:
                            # Should have context when chunks pass threshold
                            self.assertTrue(result['context_used'] or 'Computer Science' in result['response'])
                        else:
                            # Should return fallback when no chunks pass threshold
                            self.assertIn('Computer Science', result['response'])
                            
                finally:
                    # Restore original threshold
                    self.rag_service.search_threshold = original_threshold
    
    def test_conversational_interactions_allowed(self):
        """Test that conversational interactions are properly allowed"""
        conversational_queries = [
            "Hi",
            "Hello", 
            "Thank you",
            "What can you help with?",
            "How are you?",
            "Good morning"
        ]
        
        for query in conversational_queries:
            with self.subTest(query=query):
                # Mock empty chunks (no context)
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=[]):
                    # Mock a friendly conversational response
                    with patch.object(self.rag_service, '_generate_llm_response') as mock_llm:
                        mock_llm.return_value = {
                            'content': f'Hello! I\'m here to help you with your Computer Science materials.',
                            'usage': {'total_tokens': 20}
                        }
                        
                        result = self.rag_service.generate_response(
                            query=query,
                            subject_id=self.comp_sci_subject.id,
                            chat_history=[],
                            user_id=self.user.id
                        )
                        
                        # Should not get fallback message for conversational queries
                        self.assertNotIn("couldn't find information", result['response'].lower())
                        
                        # Should get some kind of friendly response
                        self.assertTrue(len(result['response'].strip()) > 0)
                        self.assertIn("help", result['response'].lower())

    def test_conversational_vs_academic_distinction(self):
        """Test that system distinguishes between conversational and academic queries"""
        test_cases = [
            {
                'query': 'Hi there!',
                'is_conversational': True,
                'should_get_fallback': False
            },
            {
                'query': 'What is machine learning?',
                'is_conversational': False,
                'should_get_fallback': True  # No context provided
            },
            {
                'query': 'Thank you for your help',
                'is_conversational': True,
                'should_get_fallback': False
            },
            {
                'query': 'Explain neural networks',
                'is_conversational': False,
                'should_get_fallback': True  # No context provided
            }
        ]
        
        for case in test_cases:
            with self.subTest(query=case['query']):
                # Test conversational detection
                is_conversational = self.rag_service._is_conversational_query(case['query'])
                self.assertEqual(is_conversational, case['is_conversational'])
                
                # Test response behavior 
                with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=[]):
                    if case['is_conversational']:
                        # Mock friendly response for conversational
                        with patch.object(self.rag_service, '_generate_llm_response') as mock_llm:
                            mock_llm.return_value = {
                                'content': 'I\'m here to help with your materials!',
                                'usage': {'total_tokens': 15}
                            }
                            
                            result = self.rag_service.generate_response(
                                query=case['query'],
                                subject_id=self.comp_sci_subject.id,
                                chat_history=[],
                                user_id=self.user.id
                            )
                    else:
                        # Academic queries should get fallback with no context
                        result = self.rag_service.generate_response(
                            query=case['query'],
                            subject_id=self.comp_sci_subject.id,
                            chat_history=[],
                            user_id=self.user.id
                        )
                    
                    contains_fallback = "couldn't find information" in result['response'].lower()
                    self.assertEqual(contains_fallback, case['should_get_fallback'])

    def test_automated_validation_pipeline(self):
        """Test automated pipeline for validating all responses"""
        test_scenarios = [
            {
                'query': 'What is machine learning?',
                'expected_behavior': 'fallback',
                'chunks': []
            },
            {
                'query': 'What is DDL?', 
                'expected_behavior': 'material_response',
                'chunks': self.mock_relevant_chunks
            },
            {
                'query': 'Who invented computers?',
                'expected_behavior': 'fallback', 
                'chunks': []
            }
        ]
        
        validation_results = []
        
        for scenario in test_scenarios:
            with patch.object(self.rag_service, '_retrieve_relevant_chunks', return_value=scenario['chunks']):
                if scenario['expected_behavior'] == 'material_response':
                    with patch.object(self.rag_service, '_generate_llm_response') as mock_llm:
                        mock_llm.return_value = {
                            'content': 'Based on your materials, DDL stands for Data Definition Language.',
                            'usage': {'total_tokens': 30}
                        }
                        
                        result = self.rag_service.generate_response(
                            query=scenario['query'],
                            subject_id=self.comp_sci_subject.id,
                            chat_history=[],
                            user_id=self.user.id
                        )
                else:
                    result = self.rag_service.generate_response(
                        query=scenario['query'],
                        subject_id=self.comp_sci_subject.id,
                        chat_history=[],
                        user_id=self.user.id
                    )
                
                # Validate response meets expectations
                if scenario['expected_behavior'] == 'fallback':
                    validation_passed = 'Computer Science' in result['response'] and not result['context_used']
                else:
                    validation_passed = result['context_used'] and 'Computer Science materials' not in result['response']
                
                validation_results.append({
                    'query': scenario['query'],
                    'expected': scenario['expected_behavior'],
                    'passed': validation_passed,
                    'response': result['response'][:100] + '...'
                })
        
        # All validations should pass
        failed_validations = [v for v in validation_results if not v['passed']]
        if failed_validations:
            self.fail(f"Validation failures: {failed_validations}")
        
        # Log successful validation
        print(f"\n✅ Automated validation pipeline passed all {len(validation_results)} scenarios")

class RAGEnforcementIntegrationTestCase(TestCase):
    """Integration tests for RAG enforcement in real scenarios"""
    
    def setUp(self):
        """Set up integration test data"""
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com', 
            password='testpass123'
        )
        
        self.subject = Subject.objects.create(
            user=self.user,
            name='Database Systems'
        )
        
    def test_end_to_end_enforcement(self):
        """Test end-to-end enforcement with real data flow"""
        # This would test the full pipeline from chat API to response
        # In a real scenario, this would make actual HTTP requests
        # to the chat endpoints and validate responses
        pass
        
    def test_performance_with_enforcement(self):
        """Test that enforcement doesn't significantly impact performance"""
        # This would measure response times with and without enforcement
        # to ensure the validation layers don't cause unacceptable delays
        pass

if __name__ == '__main__':
    unittest.main() 