import csv
from datetime import datetime
from math import ceil

from flask import Flask, render_template, request

from extensions import cors, db
from models import Course, Category


app = Flask(__name__)
app.config.from_pyfile('settings.py')
cors.init_app(app)
db.init_app(app)




# @app.get('/c/')
# def t1():
#     data = get_cats()
#     return str(data)

# .objects(search_text__icontains=search_query)



@app.get('/')
@app.get('/<category>/')
def test(category=None):
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 12))
    #
    if category:
        posts = Course.objects(is_free=False, category=category).order_by('-discount_percentage').skip(page_size*(page-1)).limit(page_size)
        count = Course.objects(is_free=False, category=category).count()
    else:
        posts = Course.objects(is_free=False).order_by('-discount_percentage').skip(page_size*(page-1)).limit(page_size)
        count = Course.objects(is_free=False).count()
    #
    pages_count = ceil(count / page_size)
    previous_pages = list(range(1, page))
    next_pages = list(range(page, pages_count+1))
    pages = previous_pages[-5:] + next_pages[:5]
    #
    categories = Category.objects
    #
    data = {
        'posts': posts,
        'pages': pages,
        'current_page': page,
        'last_page': pages_count,
        'categories': categories,
        'category': category or '',
    }
    return render_template('3.html', data=data)



if __name__ == '__main__':
    app.run(debug=True)
