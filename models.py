
from flask_mongoengine import Document
from mongoengine import StringField, IntField, BooleanField, DateTimeField, URLField


class Course(Document):
    syllabus = StringField()   # فقط سر فصل ها را ذخیره می کند
    about = StringField()
    chapters = StringField()   # سرفصل ها به همراه جزئیات هر جلسه را ذخیره می کند
    certificate = BooleanField()
    title = StringField(required=True)
    date = DateTimeField()
    main_price = IntField()
    course_id = IntField(required=True)
    discounted_price = IntField()
    discount_percentage = IntField()
    course_url = URLField(required=True)         # Full course URL
    img_url = StringField()
    has_discount = BooleanField()
    category_1 = StringField()
    category_2 = StringField()
    category_3 = StringField()
    website = StringField()
    affiliate_link = StringField()
    description = StringField()       # A compelete Markdown based description with a combination of Summary, Seasons, about, chapters and certificate
    short_url = StringField()
    course_time = StringField()
    course_url_name = StringField()   # Just name of course URL
    Teacher = StringField()
    duration = StringField()
    category_English = StringField()
    tag = StringField()
    is_free = BooleanField()
    search_text = StringField()
    meta = dict(
        indexes=[
            'title', 'date', 'main_price',
            'discount_percentage', 'is_free',
            'category_1', 'website', 'Teacher', 'tag', 'category_English',
            {
            'fields': ['$title', '$tag', '$category_1', '$Teacher'],
            'default_language': 'none',
            'weights': {
                'title': 10,
                'tag': 5,
                'category_1': 1,
                'Teacher': 4,
            }
        }
        ]
    )

class Course_prime(Document):
    course_id = StringField()
    title = StringField()
    datetime = DateTimeField()
    teacher = StringField()
    main_price = IntField()
    discounted_price = IntField()
    discount_percentage = IntField()
    has_discount = BooleanField()
    img_url = StringField()
    course_url = StringField()
    duration = StringField()
    category = StringField()
    website = StringField()
    affiliate_link = StringField()
    description = StringField()
    summary = StringField()
    seasons = StringField()
    shamsi_date = StringField()
    course_url_name = StringField()
    rephrased_desc = StringField()
    is_free = BooleanField()
    search_text = StringField()

    meta = dict(
        indexes=[
            'title', 'datetime', 'main_price',
            'discount_percentage', 'is_free',
            'category', 'website'
        ]
    )

class Category(Document):
    name = StringField()    # English name of category
    title = StringField()   # Persian name of category
    meta = dict(
        indexes=['name']
    )

class OptimizedCourse(Document):
    course_id = IntField(required=True)
    website = StringField(required=True)
    original_description = StringField(required=True)
    new_description = StringField(required=True)
    short_description = StringField()
    is_generated = BooleanField(default=True)
    generated_at = DateTimeField()
    cta = StringField()
    meta_description = StringField()

    meta = {
        'collection': 'optimized_courses',
        'indexes': [
            {'fields': ['course_id', 'website'], 'unique': True},
            'is_generated',
            '-generated_at',  # Descending index for sorting
            {
                'fields': ['$new_description'],
                'default_language': 'none',
                'weights': {
                    'new_description': 1
                }
            }
        ]
    }

class ContactMessages(Document):
    name = StringField()    # User's name
    email = StringField()   # User's email
    message = StringField() # User's message
    date = DateTimeField()  # Date of message
    meta = dict(
        indexes=['name']
    )

class Config(Document):
    course_source = StringField(default='Course')

    meta = dict()