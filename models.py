
from flask_mongoengine import Document
from mongoengine import StringField, IntField, BooleanField, DateTimeField


class Course(Document):
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

    meta = dict(
        indexes=[
            'title', 'datetime', 'main_price', 
            'discount_percentage', 'is_free', 
            'category', 'website'
        ]
    )