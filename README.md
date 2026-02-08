# Holy Cross School Website - Quick Start Guide

## Running the Development Server

1. **Activate Virtual Environment:**
   ```bash
   cd "/Volumes/Drive A/Rajshahi Holy Cross/Final Website"
   source venv/bin/activate
   ```

2. **Create Admin User (First Time Only):**
   ```bash
   python manage.py createsuperuser
   ```
   Follow prompts to create username, email, and password.

3. **Start Server:**
   ```bash
   python manage.py runserver
   ```

4. **Access the Website:**
   - Homepage: http://localhost:8000
   - Admin Panel: http://localhost:8000/admin

## Adding Content

### Step 1: School Information
1. Go to Admin → School Information
2. Fill in:
   - History, Mission, Vision
   - Principal & Vice Principal details with photos
   - Contact information
   - Social media links

### Step 2: Hero Slider
1. Admin → Sliders → Add Slider
2. Upload high-resolution images (1920x800px recommended)
3. Set order (0, 1, 2, etc.)
4. Mark as active

### Step 3: Facts & Figures
1. Admin → Facts & Figures
2. Add statistics like:
   - Students: "5000+"
   - Teachers: "150+"
   - Years: "75"
3. Use Font Awesome icon classes: `fa-users`, `fa-chalkboard-teacher`, `fa-award`

### Step 4: Teachers
1. Admin → Teachers → Add Teacher
2. Upload photo (400x400px recommended)
3. Set order for display sequence

### Step 5: Notices
1. Admin → Notices → Add Notice
2. Mark important notices to appear in ticker
3. Attach PDFs or images if needed

### Step 6: News
1. Admin → News Items → Add News Item
2. Mark as "Featured" to appear on homepage
3. Add featured image (800x600px)

### Step 7: Clubs
1. Admin → Clubs → Add Club
2. Upload logo (300x300px)
3. Fill in description and objectives

### Step 8: Resources
1. Admin → Resources → Add Resource
2. Upload files or add external links
3. Categorize (Syllabus, Rules, etc.)

## Folder Structure

- **static/images/** - Place static images here
- **media/** - Uploaded content goes here (auto-created)
- **templates/** - HTML templates
- **venv/** - Virtual environment (don't edit)

## Troubleshooting

**Server won't start:**
- Make sure virtual environment is activated
- Check if another server is running on port 8000

**Changes not showing:**
- Hard refresh browser (Cmd+Shift+R on Mac)
- Clear browser cache

**Images not displaying:**
- Verify DEBUG=True in settings.py
- Check file paths are correct
- Ensure files are in media/ or static/images/

## Production Deployment

See walkthrough.md for detailed production setup including:
- PostgreSQL database migration
- Static files collection
- Security configuration
- Domain setup

## Support

For customization or issues, refer to:
- walkthrough.md - Complete documentation
- implementation_plan.md - Architecture details
- Django documentation: https://docs.djangoproject.com/
