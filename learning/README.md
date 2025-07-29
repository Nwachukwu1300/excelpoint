# Learning App - Automatic Data Loading

## Overview
The Learning app automatically loads initial courses, achievements, and learning resources when the Django application starts.

## Automatic Data Loading

### How It Works
1. **Migration-Based Loading**: The `0006_load_initial_data.py` migration automatically loads initial data when `python manage.py migrate` is run
2. **App Ready Signal**: The `apps.py` file includes a signal that loads data when the app is ready (if no data exists)
3. **Management Command**: Use `python manage.py load_initial_data` for manual control

### Initial Data Includes
- **12 Courses**: Python, JavaScript, Data Science, Machine Learning, React, Database Design, AWS, Cybersecurity, UI/UX, DevOps, Flutter, AI
- **8 Achievements**: First Steps, Course Collector, Quiz Champion, Subject Explorer, Course Master, AI Assistant, Material Curator, Perfect Score
- **8 Learning Resources**: Official documentation, tutorials, and course links

### Management Commands

#### Load Initial Data
```bash
python manage.py load_initial_data
```

#### Force Reload Data
```bash
python manage.py load_initial_data --force
```

#### Clear and Reload Data
```bash
python manage.py load_initial_data --clear
```

### Fixtures
- **Location**: `learning/fixtures/initial_data.json`
- **Regeneration**: Run `python manage.py dumpdata learning.Course learning.Achievement learning.LearningResource --indent 2 > learning/fixtures/initial_data.json`

### Benefits
- ✅ **Automatic Setup**: No manual data population needed
- ✅ **Version Controlled**: Data is part of the codebase
- ✅ **Fast Loading**: Uses Django's optimized fixture loading
- ✅ **Safe**: Won't overwrite existing data unless forced
- ✅ **Flexible**: Multiple ways to load data (migration, signal, command)

## Development Workflow

### For New Developers
1. Clone the repository
2. Run `python manage.py migrate` (automatically loads initial data)
3. Start developing - courses are already available!

### For Data Updates
1. Modify the `populate_courses.py` command if needed
2. Run `python manage.py populate_courses --clear` to regenerate data
3. Update the fixture: `python manage.py dumpdata learning.Course learning.Achievement learning.LearningResource --indent 2 > learning/fixtures/initial_data.json`
4. Commit the updated fixture

### For Production
- The migration ensures data is loaded during deployment
- The app ready signal provides a backup loading mechanism
- Use `--force` flag if you need to reload data in production 