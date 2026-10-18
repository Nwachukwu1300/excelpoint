# ExcelPoint - Learning Enhancement Platform

## 🎥 [Watch Demo Video](https://drive.google.com/file/d/1yBZ8Cexa4Lhrnot7D3OiEqdqtsfgFxn5/view)

## Project Overview
ExcelPoint is a learning enhancement platform designed to elevate the educational experience for everyone. My platform combines advanced content processing, interactive learning tools, and personalized study assistance to transform how people learn and retain knowledge.

## Mission
To bridge the gap between traditional learning methods and modern educational needs by providing intelligent, adaptive learning experiences that cater to diverse learning styles and professional requirements.

## **What Makes ExcelPoint Special - Core Features**

### **🔐 Advanced Authentication & Security**
- **Google OAuth Integration** - Seamless login with Google accounts
- **Session Management** - Secure, persistent user sessions with timeout controls
- **JWT Token Support** - RESTful API authentication
- **Role-Based Access Control** - User permissions and admin management
- **Secure File Uploads** - Validation and sanitization for all file types

### **🧠 Intelligent Content Processing Engine**
- **Multi-Format Support** - PDF, DOCX, Word documents, videos, audio files
- **Smart Content Chunking** - Intelligent document segmentation for optimal learning
- **Vector Embeddings** - Advanced semantic search using sentence transformers
- **Real-Time Processing** - Background task processing with Celery and Redis
- **Content Validation** - File type verification and security checks

### **💬  Chat System**
- **Context-Aware Conversations** - Chatbot remembers entire conversation history
- **Session Persistence** - Chat sessions saved and restored across browser sessions
- **Material Integration** - AI responses based on your uploaded study materials
- **Smart Caching** - Intelligent response caching to reduce API costs
- **Conversation Memory** - Bot remembers previous discussions and user preferences

### **📚 Dynamic Learning Tools**
- **AI-Generated Quizzes** - Automatic quiz creation from uploaded materials
- **Smart Flashcards** - Personalized flashcard generation with spaced repetition
- **Adaptive Learning Paths** - Content recommendations based on user progress
- **Progress Tracking** - Detailed analytics and learning insights
- **Achievement System** - Gamified learning with milestones and badges

### **🔄 Real-Time Processing & Background Tasks**
- **Celery Worker System** - Asynchronous processing for heavy operations
- **Redis Message Broker** - Fast, reliable task queuing and caching
- **Background File Processing** - Non-blocking document analysis
- **Task Monitoring** - Real-time status updates for long-running operations
- **Error Recovery** - Automatic retry mechanisms for failed tasks

### **☁️ Cloud-Ready Architecture**
- **Storage Abstraction** - Seamless switching between local and S3 storage
- **AWS S3 Integration** - Scalable cloud storage for media files
- **Environment Configuration** - Flexible deployment across different environments
- **Docker Support** - Containerized deployment ready
- **Horizontal Scaling** - Architecture supports multiple worker instances

### **📱 Modern Frontend Experience**
- **React 18 with TypeScript** - Latest frontend technologies
- **Responsive Design** - Works perfectly on desktop, tablet, and mobile
- **Real-Time Updates** - Live chat and progress updates
- **Modern UI/UX** - Clean, intuitive interface design
- **Progressive Web App** - App-like experience in the browser

### **🗄️ Robust Data Management**
- **PostgreSQL Database** - Enterprise-grade data storage
- **Advanced Querying** - Optimized database queries with proper indexing
- **Data Migration System** - Safe database schema evolution
- **Backup & Recovery** - Data protection and restoration capabilities
- **Performance Optimization** - Database query optimization and caching

### **🔍 Advanced Search & Discovery**
- **Semantic Search** - Find content by meaning, not just keywords
- **Vector Similarity** - AI-powered content matching
- **Subject Organization** - Hierarchical content categorization
- **Smart Filtering** - Advanced content filtering and sorting
- **Search Analytics** - Track what users are searching for

### **📊 Comprehensive Analytics & Insights**
- **User Behavior Tracking** - Detailed learning pattern analysis
- **Performance Metrics** - Quiz scores, completion rates, time spent
- **Content Analytics** - Which materials are most effective
- **Progress Visualization** - Charts and graphs for learning progress
- **Export Capabilities** - Download reports and analytics data

### **🛠️ Developer Experience & Maintainability**
- **Comprehensive Documentation** - Every module and function documented
- **Type Safety** - Full TypeScript support for frontend
- **Testing Framework** - Vitest setup for frontend testing
- **Code Quality** - Linting and formatting standards
- **Modular Architecture** - Clean separation of concerns

### **🚀 Production Ready Features**
- **Environment Configuration** - Separate settings for dev/staging/prod
- **Logging & Monitoring** - Comprehensive error tracking and debugging
- **Security Headers** - CSRF protection, XSS prevention
- **Rate Limiting** - API abuse prevention
- **Error Handling** - Graceful error handling with user-friendly messages

## Technical Architecture

### **Backend Stack**
- **Framework**: Django 5.2.1 with Python 3.13
- **Database**: PostgreSQL with advanced querying
- **Content Processing**: LangChain, Sentence Transformers, OpenAI integration
- **Task Processing**: Celery with Redis for background tasks
- **Content Processing**: Unstructured.io for document analysis

### **Frontend & UI**
- **Framework**: React with TypeScript
- **Styling**: Modern CSS with responsive design
- **Real-time Features**: WebSocket integration for live chat
- **User Experience**: Intuitive, accessible interface design

### **Smart Features & Machine Learning**
- **Content Analysis**: Advanced NLP for document processing
- **Vector Search**: Semantic search capabilities
- **Chat Intelligence**: Context-aware responses
- **Learning Optimization**: Adaptive algorithms for personalized experience

## How XP answers (RAG pipeline)

XP answers **only from your uploaded materials**:

1. Your question is embedded (all-MiniLM-L6-v2) and matched against your chunks in Postgres (pgvector, HNSW index).
2. If nothing scores above the similarity threshold, XP says it isn't in your materials and no LLM is called.
3. Otherwise the reasoning pipeline runs: retrieve → generate (strict, cited) → verify claims → retry if unfaithful. Follow-ups ("give an example of that") are first rewritten using the chat history. That's 2 LLM calls for a normal question, 3 for a follow-up.
4. Every answer is saved as a trace and scored (faithfulness, unsupported-claim rate, retrieval similarity).

### Evaluation and debugging

| What | Where |
|---|---|
| Quality dashboard (trends, failures, retrieval stats) | `/insights/` |
| Per-answer trace (chunks, prompts, claims, stage timings) | `/insights/<session-id>/`, or "How was this answered?" in the chat |
| Quality data as JSON | `GET /api/reasoning/quality/?days=30` |
| Retrieval benchmark (hit@k, MRR) | `python manage.py benchmark_retrieval docs/retrieval_benchmark.example.json` |
| LLM-judge scoring (optional, costs one call per answer) | set `EVAL_LLM_JUDGE=True`, or run `python manage.py judge_answers` |

### Study workflows

After an upload is processed, a Celery chord generates flashcards, a quiz and a summary in parallel, then sends a notification (bell icon). Flashcards are scheduled with SM-2 spaced repetition (`/subjects/<id>/review/`), a daily beat job reminds you when cards are due, and the Study Dashboard suggests next steps from your quiz scores, due cards and questions your notes couldn't answer.

Each answer also logs one JSON line (`"event": "chat_answer"`) with its path, chunk count, verification and per-stage timings.

## Getting Started

### Prerequisites
- Python 3.13+
- Node.js 18+
- PostgreSQL 13+ with the [pgvector](https://github.com/pgvector/pgvector) extension (0.8+)
- Redis 6+

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd excelpoint
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up frontend**
   ```bash
   npm install
   npm run build
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and API credentials
   ```

5. **Install pgvector, then run migrations**
   ```bash
   # Postgres 17/18 via Homebrew: brew install pgvector
   # Other versions: build it against your server's pg_config
   git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
   cd pgvector && make PG_CONFIG=$(which pg_config) && make install PG_CONFIG=$(which pg_config)

   python manage.py migrate   # enables the extension and converts embeddings
   ```

6. **Start services**
   ```bash
   # Terminal 1: Django server
   python manage.py runserver
   
   # Terminal 2: Celery worker
   celery -A config.celery.app worker --loglevel=INFO
   
   # Terminal 3: Redis
   redis-server

   # Terminal 4: Celery beat (daily flashcard review reminders)
   celery -A config.celery.app beat --loglevel=INFO
   ```

## Demo & Screenshots

🎥 **[Watch the full demo video](https://drive.google.com/file/d/1yBZ8Cexa4Lhrnot7D3OiEqdqtsfgFxn5/view)** to see ExcelPoint in action!

## Contributing

I'm welcoming contributors



## Support
 Contact the mnfinance@gmail.com

---

**Built with ❤️ by Mmesoma**

