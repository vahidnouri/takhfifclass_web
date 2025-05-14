
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
    new_description = StringField()   # A description that would be updated through deepseek later
    short_url = StringField()
    course_time = StringField()
    course_url_name = StringField()   # Just name of course URL
    shamsi_date = StringField()
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
            'category_1', 'website'
        ]
    )


class Category(Document):
    name = StringField()    # English name of category
    title = StringField()   # Persian name of category

    meta = dict(
        indexes=['name']
    )

class OptimizedCourse(Document):
    course_id = IntField(required=True, unique=True)
    website = StringField(required=True)
    original_description = StringField(required=True)
    new_description = StringField(required=True)
    is_generated = BooleanField(default=True)
    generated_at = DateTimeField()
    cta = StringField()
    meta_description = StringField()
    meta = {
        'collection': 'optimized_courses'
    }