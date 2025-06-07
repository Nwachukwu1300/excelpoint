# Career Nexus - Career Development Platform

## Project Overview
Career Nexus is a comprehensive career development platform that helps users manage their professional growth through learning management, progress tracking, and career development tools.

## Current Implementation Status

### Completed Features
- **User Authentication System**
 - Registration with email validation
 - Login/Logout functionality
 - Profile management with achievements, certifications, and education
 - Password change capabilities
 - Session-based authentication

- **Learning Management System**
 - Course catalog and progress tracking
 - Learning dashboard with statistics
 - Resource library with external learning materials
 - Achievement system and learning streaks
 - Saved resources functionality

- **User Profile Management**
 - Comprehensive user profiles
 - Achievement tracking
 - Certification management
 - Education history
 - Profile completion tracking

### Pending Features
- **API Integrations**
 - Learning platforms (Coursera, Udemy)
 - Portfolio integration
 - Trend analysis
- **Core Functionality**
 - Market trend analysis
 - Advanced course recommendations

## Technical Stack
- **Backend**: Django/Python
- **Database**: SQLite (development) / PostgreSQL (production)
- **Authentication**: Session-based
- **API Framework**: Django REST Framework
- **Frontend**: Bootstrap 5, HTML/CSS/JavaScript

## Getting Started

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Installation
1. Clone the repository
2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Features Overview

### Learning Dashboard
- Track course progress and completion
- View learning statistics and achievements
- Monitor learning streaks
- Access personalized recommendations

### Resource Library
- Browse external learning resources
- Save resources for later
- Filter by platform and difficulty level
- Track resource usage

### User Profiles
- Manage personal information
- Track achievements and certifications
- View learning progress
- Profile completion tracking

