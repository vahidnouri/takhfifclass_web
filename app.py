import csv
import json
from datetime import datetime
from math import ceil

from khayyam import JalaliDate
from persian import convert_en_numbers
from flask import Flask, render_template, request, send_from_directory

from extensions import cors, db
from models import Course, Category


app = Flask(__name__)
app.config.from_pyfile('settings.py')
cors.init_app(app)
db.init_app(app)


app.jinja_env.filters.update(
    persian=convert_en_numbers,
    persian_price=lambda x: convert_en_numbers(f'{x:,}'),
    persian_date=lambda x: convert_en_numbers(JalaliDate(x).strftime('%d %B %Y')),
    persian_site=lambda x: {'Limoonad': 'لیموناد'}.get(x, x),
)

# @app.get('/favicon.ico')
# def favicon():
#     return send_from_directory('static', 'favicon.png', mimetype='image/vnd.microsoft.icon')



@app.get('/')
@app.get('/<category>/')
def courses(category=None):
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    search_query = request.args.get('q', '')
    #
    filters = {'is_free': False}
    if category:
        filters['category'] = category
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
    category_menu = {i.title: i.title for i in categories}
    #
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
    }
    return render_template('home.html', data=data)


@app.get('/<website>/<course_id>/')
@app.get('/<website>/<course_id>/<title>/')
def get_course(website, course_id):
    post = Course.objects(website=website, course_id=course_id).first()
    #
    data = {
        'post': post,
        'related_posts': [],
    }
    return render_template('4.html', data=data)



@app.get('/home/')
def home():
    return render_template('example.html')


@app.get('/api/s/<query>/')
def search(query):
    result = [
        {},
        {},
        {},
    ]
    return json.dumps(result)


if __name__ == '__main__':
    app.run(debug=True)
