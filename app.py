import csv
from datetime import datetime
from math import ceil

from flask import Flask, render_template, request

from extensions import cors, db
from models import Course


app = Flask(__name__)
app.config.from_pyfile('settings.py')
cors.init_app(app)
db.init_app(app)



# @app.get('/<string:course_id>/')
# def t1(course_id):
#     data = Course.objects.get(course_id=course_id).to_mongo().to_dict()
#     return str(data)




@app.get('/')
def test():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 12))
    #
    posts = Course.objects(is_free=False).order_by('-discount_percentage').skip(page_size*(page-1)).limit(page_size)
    count = Course.objects.count()
    pages_count = ceil(count / page_size)
    previous_pages = list(range(1, page))
    next_pages = list(range(page, pages_count+1))
    pages = previous_pages[-5:] + next_pages[:5]
    #
    data = {
        'posts': posts,
        'pages': pages,
        'current_page': page,
        'last_page': pages_count,
    }
    return render_template('3.html', data=data)



if __name__ == '__main__':
    app.run(debug=True)
