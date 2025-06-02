import csv
import json
from datetime import datetime
from math import ceil
import re
import markdown 
from khayyam import JalaliDate
from persian import convert_en_numbers
from flask import Flask, render_template, request, abort, redirect, url_for, flash
from flask import jsonify
from mongoengine.connection import get_db
import os
from extensions import cors, db
from models import Course, Category, OptimizedCourse, ContactMessages
import os



app = Flask(__name__)
app.config.from_pyfile('settings.py')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback-secret')
cors.init_app(app)
db.init_app(app)

db2 = get_db()
contact_collection = ContactMessages.objects

app.jinja_env.filters.update(
    persian=convert_en_numbers,
    persian_price=lambda x: convert_en_numbers(f'{x:,}'),
    persian_date=lambda x: convert_en_numbers(JalaliDate(x).strftime('%d %B %Y')),
    persian_site=lambda x: {'Limoonad': 'لیموناد', 'Maktabkhooneh': 'مکتبخونه'}.get(x, x)
,
)

# @app.get('/favicon.ico')
# def favicon():
#     return send_from_directory('static', 'favicon.png', mimetype='image/vnd.microsoft.icon')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    # Get course categories for the dropdown menu
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}

    if request.method == 'POST':
        # Create and save using MongoEngine
        message = ContactMessages(
            name=request.form['name'],
            email=request.form['email'],
            message=request.form['message'],
            date=datetime.utcnow()
        )
        message.save()

        flash('پیام شما با موفقیت ارسال شد. با تشکر!')
        return redirect(url_for('contact'))

    data = {
        'menu': category_menu,
        'page': 'contact',
        'page_name': 'تماس با ما'
    }

    return render_template('contact.html', data=data)

@app.route('/about')
def about():
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}
    data = {
        'menu': category_menu,
    }
    return render_template('about.html', data=data)

@app.get('/')
@app.get('/<category>/')
def courses(category=None):
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    search_query = request.args.get('q', '')
    #
    filters = {'is_free': False}
    if category:
        filters['category_English'] = category
    if search_query:
        filters = {'search_text__icontains': search_query}
        category = None
    #
    posts = Course.objects(**filters).order_by('-discount_percentage').skip(page_size*(page-1)).limit(page_size)
    count = Course.objects(**filters).count()
    #
    pages_count = ceil(count / page_size)
    previous_pages = list(range(1, page))
    next_pages = list(range(page, pages_count+1))
    pages = previous_pages[-2:] + next_pages[:3]
    #
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}
    #
    # List all images in the 'static/images' folder
    images_folder = os.path.join(app.static_folder, 'images')
    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')

    category_cards = []
    for cat in categories[:10]:  # Limit to 10
        # Try to find an image file matching the category English name
        image_filename = None
        for ext in image_extensions:
            candidate = f"{cat.name}{ext}"
            if os.path.exists(os.path.join(images_folder, candidate)):
                image_filename = candidate
                break
        # If not found, use a default image
        if not image_filename:
            image_filename = "default.png"
        category_cards.append({
            "name": cat.name,      # English, for URL
            "title": cat.title,    # Persian, for display
            "image": image_filename
        })
    data = {
        'posts': posts,
        'pages': pages,
        'current_page': page,
        'last_page': pages_count,
        'categories': categories,
        'category': category or '',
        'search_query': search_query,
        'page': 'home',
        'menu': category_menu,
        "category_cards": category_cards,  # Pass image paths to template
    }
    return render_template('home.html', data=data)


@app.get('/<website>/<course_id>/')
@app.get('/<website>/<course_id>')
@app.get('/<website>/<course_id>/<course_url_name>')
def home(website, course_id, course_url_name=None):
    course = Course.objects(course_id=course_id, website=website).first()
    new_desc = OptimizedCourse.objects(course_id=course_id, website=website).first()
    
    if not course:
        abort(404, "چنین کلاسی یافت نشد.")
    # course.description_html = markdown.markdown(course.description)
    related_courses = list(db2.course.aggregate([
    {"$match": {"category_1": course.category_1, "_id": {"$ne": course.id}}},
    {"$sample": {"size": 3}}
    ]))

    
    # Create preview safely from raw Markdown
    raw_description = new_desc.new_description if new_desc else course.description or ""
    cta = new_desc.cta if new_desc else "از لینک زیر ثبت نام کنید"
    meta = new_desc.meta_description if new_desc else ""
    raw_preview = raw_description[:300] + "..."

    full_desc = markdown.markdown(raw_description, extensions=['tables'] )
    preview_desc = markdown.markdown(raw_preview, extensions=['tables'] )
    full_desc = full_desc.replace('<table>', '<table class="table table-bordered table-striped">')
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}
    data = {'title': course.title,
            'short_description': preview_desc,
            'course_image': course.img_url,
            'full_description': full_desc,
            'main_price': course.main_price,
            'discounted_price': course.discounted_price,
            'discount_percentage': course.discount_percentage,
            'class_link': course.affiliate_link,
            'course_name': course.course_url_name,
            'related_courses': related_courses,
            'cta': cta,
            'meta': meta,
            'menu': category_menu,
            }
    return render_template('example.html', data=data)


@app.get('/api/s/<query>/')
def search(query):
    regex = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)

    results = Course.objects.filter(
        __raw__={
            "$or": [
                {"title": regex},
                {"tags": regex},
                {"category_1": regex},
                {"description": regex},
            ]
        }
    )

    response = []
    for course in results:
        response.append({
            "title": course.title,
            "description": course.category_1,
            "url": f"/{course.website}/{course.course_id}/",
        })

    return jsonify(response)



@app.route('/search/<query>')
def full_results(query):
    regex = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)
    results = Course.objects.filter(
        __raw__={
            "$or": [
                {"title": regex},
                {"tags": regex},
                {"Teacher": regex},
                {"category_1": regex},
                {"description": regex},
            ]
        }
    )
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    #
    posts = results.order_by('-discount_percentage').skip(page_size*(page-1)).limit(page_size)
    count = results.count()
    #
    pages_count = ceil(count / page_size)
    previous_pages = list(range(1, page))
    next_pages = list(range(page, pages_count+1))
    pages = previous_pages[-2:] + next_pages[:3]
    #
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}

    data = {
        'keywords': [query],
        'menu': category_menu,
        'posts': posts,
        'pages': pages,
        'current_page': page,
        'last_page': pages_count,
    }
    return render_template("search_results.html", courses=results, query=query, data=data)

# if __name__ == '__main__':
#     app.run(debug=True)
