from datetime import datetime, timedelta
from math import ceil
import re
import markdown
from persian import convert_en_numbers
from flask import Flask, render_template, request, abort, redirect, url_for, flash, send_from_directory
from flask import jsonify, Response
from mongoengine.connection import get_db
import os
from extensions import cors, db
from models import Course, Category, OptimizedCourse, ContactMessages, Course_prime, Config
import os
from urllib.parse import urlencode, quote_plus
from persiantools.jdatetime import JalaliDateTime
from zoneinfo import ZoneInfo
from flask import redirect
import time
import ast


# Persian month names
PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]
SEARCH_RANKING = {

    # Base
    "discount_weight": 1,

    # Provider
    "preferred_provider": "limoonad",
    "preferred_provider_bonus": 30,

    # Price
    "price_bonus": [
        (5_000_000, 40),
        (3_000_000, 30),
        (1_000_000, 20),
    ],

    # Keywords
    "keyword_bonus": 10,
    "keywords": [
                "جامع",
                "کامل",
                "پیشرفته",
                "صفر",
                "پکیج",
                "مستر",
                "ویژه",
                "سریع",
                "پشتیبانی",
                "جدید",
                "حرفه‌ای",
                "همه",
                "مخصوص",
            ]
}

def course_score(course):

    score = 0

    # ------------------------------
    # Discount
    # ------------------------------
    score += (course.discount_percentage or 0) * SEARCH_RANKING["discount_weight"]

    # ------------------------------
    # Preferred Provider
    # ------------------------------
    if course.website == SEARCH_RANKING["preferred_provider"]:
        score += SEARCH_RANKING["preferred_provider_bonus"]

    # ------------------------------
    # Price
    # ------------------------------
    price = course.main_price or 0

    for limit, bonus in SEARCH_RANKING["price_bonus"]:
        if price >= limit:
            score += bonus
            break

    # ------------------------------
    # Keywords
    # ------------------------------
    title = (course.title or "").lower()

    for keyword in SEARCH_RANKING["keywords"]:
        if keyword.lower() in title:
            score += SEARCH_RANKING["keyword_bonus"]

    return score

app = Flask(__name__)
app.config.from_pyfile('settings.py')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback-secret')
# app.url_map.strict_slashes = False
cors.init_app(app)
db.init_app(app)

# Matomo configuration (optional)
app.config['MATOMO_URL'] = os.getenv('MATOMO_URL', '')
app.config['MATOMO_SITE_ID'] = os.getenv('MATOMO_SITE_ID', '')


@app.context_processor
def inject_matomo():
    """Make MATOMO_URL and MATOMO_SITE_ID available in all templates.

    These come from environment variables and are empty by default.
    """
    return dict(MATOMO_URL=app.config.get('MATOMO_URL', ''), MATOMO_SITE_ID=app.config.get('MATOMO_SITE_ID', ''))

db2 = get_db()
contact_collection = ContactMessages.objects

@app.route('/favicon.ico')
@app.route('/favicon.ico/')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/x-icon')

@app.route('/.well-known/traffic-advice')
def traffic_advice():
    # Return empty 200 response or 404 if you want to indicate no advice
    return '', 200

def get_course_class():
    config = Config.objects.first()
    source = ''
    if config is not None:
        source = getattr(config, 'course_source', '') or ''
        source = source.strip().lower()

    if source == 'course_prime':
        return Course_prime
    return Course


def course_attr(course, *names, default=None):
    for name in names:
        if isinstance(course, dict):
            if name in course and course[name] is not None:
                return course[name]
        elif hasattr(course, name):
            value = getattr(course, name)
            if value is not None:
                return value
    return default


def course_public_url(course, external=False):
    """Return the canonical public URL for a course.

    Providers with a native/source ID keep the legacy three-part URL:
        /<website>/<course_id>/<course_url_name>

    Providers without a native ID may store their slug in both course_id and
    course_url_name. In that case the canonical URL is the shorter form:
        /<website>/<course_id>/

    Comparing the two values (instead of checking whether course_id is numeric)
    also supports future providers whose real native IDs are strings.
    """
    website = course_attr(course, 'website', default='')
    course_id = course_attr(course, 'course_id', default='')
    course_url_name = course_attr(course, 'course_url_name', default='')

    if website is None or course_id is None:
        return '#'

    website = str(website)
    course_id = str(course_id)
    course_url_name = str(course_url_name or '')

    if course_url_name and course_url_name != course_id:
        return url_for(
            'course',
            website=website,
            course_id=course_id,
            course_url_name=course_url_name,
            _external=external,
        )

    # Keep a trailing slash for the short/sluggified URL form.
    short_url = url_for(
        'course',
        website=website,
        course_id=course_id,
        _external=external,
    )
    return short_url.rstrip('/') + '/'


def _find_by_course_id(model, website, course_id):
    """Find a document during the int -> string migration window.

    We try the string value first (the final schema), then a legacy integer
    value when the incoming ID is purely numeric. Raw queries intentionally
    avoid MongoEngine coercing the value back to the model field type.
    """
    course_id = str(course_id)

    document = model.objects(
        __raw__={'website': website, 'course_id': course_id}
    ).first()
    if document is not None:
        return document

    if course_id.isdigit():
        return model.objects(
            __raw__={'website': website, 'course_id': int(course_id)}
        ).first()

    return None


def _course_id_variants(course_id):
    """Return values that may exist while IDs are being migrated."""
    course_id = str(course_id)
    variants = [course_id]
    if course_id.isdigit():
        variants.append(int(course_id))
    return variants


# Make one URL builder available to every Jinja template.
app.jinja_env.globals['course_url'] = course_public_url

# Custom Persian date formatter
def format_persian_date(dt):
    # Ensure datetime is timezone-aware in UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    # Convert to Tehran time
    dt_tehran = dt.astimezone(ZoneInfo("Asia/Tehran"))

    # Convert to Jalali
    jdt = JalaliDateTime(dt_tehran)
    month = PERSIAN_MONTHS[jdt.month - 1]
    return f"{jdt.day} {month} {jdt.year}"

# Register Jinja filters
app.jinja_env.filters.update(
    persian=convert_en_numbers,
    persian_price=lambda x: convert_en_numbers(f'{x:,}'),
    persian_date=lambda x: convert_en_numbers(format_persian_date(x)),
    persian_site=lambda x: {'limoonad': 'لیموناد', 'Limoonad': 'لیموناد', 'maktabkhooneh': 'مکتبخونه', 'Maktabkhooneh': 'مکتبخونه', 'novin': 'نوین', 'Novin': 'نوین',}.get(x, x)
,
)

@app.route('/robots.txt')
def robots_txt():
    return app.send_static_file('robots.txt')

@app.route('/sitemap.xml', methods=['GET'])
def sitemap():


    pages = []

    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

    # Home page
    pages.append({
        'loc': url_for('home', _external=True),
        'changefreq': 'daily',
        'priority': '1.0'
    })

    # Category pages (from your DB)
    categories = Category.objects.only('name')
    for cat in categories:
        pages.append({
            'loc': url_for('home', category=cat.name, _external=True),
            'changefreq': 'weekly',
            'priority': '0.8'
        })

    # ✅ Add course detail pages here
    # Get only top 1000 most important courses (e.g., highest discount or recently added)
    course_class = get_course_class()
    courses = course_class.objects.order_by('-discount_percentage').only('course_id', 'website', 'course_url_name')[:1000]
    for course in courses:
        pages.append({
            'loc': course_public_url(course, external=True),
            'changefreq': 'weekly',
            'priority': '0.6'
        })

    # Generate XML
    sitemap_xml = render_template('sitemap.xml', pages=pages)
    return Response(sitemap_xml, mimetype='application/xml')

@app.errorhandler(404)
def page_not_found(e):
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}
    data = {
        'menu': category_menu,
    }
    return render_template('404.html', data=data), 404

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
def home(category=None):
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    search_query = request.args.get('q', '')
    #
    course_class = get_course_class()

    # Base filters
    filter_type = request.args.get('filter')  # Optional
    filters = {}
    if filter_type == 'free':
        filters['is_free'] = True
    elif filter_type == 'discounted':
        filters['is_free'] = False
    elif filter_type == 'certificate' and course_class == Course:
        filters['certificate'] = True
    elif filter_type == 'all':
        pass
    else:
        filters['is_free'] = False  # Default fallback if not specified

    if category:
        if course_class == Course:
            filters['category_English'] = category
        else:
            filters['category'] = category
    if search_query:
        filters = {'search_text__icontains': search_query}
        category = None

    #
    posts = course_class.objects(**filters).order_by('-discount_percentage', 'id').skip(page_size*(page-1)).limit(page_size)
    count = course_class.objects(**filters).count()
    #
    pages_count = ceil(count / page_size)
    previous_pages = list(range(1, page))
    next_pages = list(range(page, pages_count+1))
    pages = previous_pages[-2:] + next_pages[:3]
    #
    # ✅ Generate page_urls
    base_args = {
        'page_size': page_size,
        'filter': filter_type or '',
        'q': search_query
    }
    page_urls = {}
    for p in pages + [1, pages_count]:  # Also add first/last
        args = base_args.copy()
        args['page'] = p
        if category:
            url_path = f"/{category}/"
        else:
            url_path = "/"
        page_urls[p] = f"{url_path}?{urlencode(args)}"

    # Build category cards
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
        'filter': filter_type or '',  # Optional
        'menu': category_menu,
        "category_cards": category_cards,  # Pass image paths to template
        'page_urls': page_urls,  # ✅ pass page_urls to template
    }
    return render_template('home.html', data=data)


@app.route("/.well-known/appspecific/com.chrome.devtools.json")
def devtools_json():
    # This function can simply return a 404 Not Found error
    # or an empty response, as this is not a path you want to serve.
    abort(404)

@app.get('/<website>/<course_id>/')
@app.get('/<website>/<course_id>')
@app.get('/<website>/<course_id>/<course_url_name>')
def course(website, course_id, course_url_name=None):
    course_id = str(course_id)
    course_class = get_course_class()
    course = _find_by_course_id(course_class, website, course_id)

    if not course:
        abort(404, "چنین کلاسی یافت نشد.")

    # Enforce exactly one canonical URL per course.
    # - Native/source ID: /website/id/slug
    # - Slug used as ID:   /website/slug/
    canonical_slug = str(course_attr(course, 'course_url_name', default='') or '')
    stored_course_id = str(course_attr(course, 'course_id', default=course_id))
    uses_long_url = bool(canonical_slug and canonical_slug != stored_course_id)

    if uses_long_url:
        if course_url_name != canonical_slug:
            return redirect(course_public_url(course), code=301)
    elif course_url_name is not None or not request.path.endswith('/'):
        return redirect(course_public_url(course), code=301)

    new_desc = _find_by_course_id(OptimizedCourse, website, stored_course_id)

    related_collection = course_class._get_collection()
    related_field = 'category_1' if course_attr(course, 'category_1') else 'category'
    related_value = course_attr(course, 'category_1', 'category')
    related_courses = []
    if related_value is not None:
        related_courses = list(related_collection.aggregate([
            {"$match": {related_field: related_value, "_id": {"$ne": course.id}}},
            {"$sample": {"size": 3}}
        ]))

    # Create preview safely from raw Markdown
    raw_description = new_desc.new_description if new_desc else course.description or ""
    cta = new_desc.cta if new_desc else "از لینک زیر ثبت نام کنید"
    meta = new_desc.meta_description if new_desc else ""
    raw_preview = raw_description[:300] + "..."

    full_desc = markdown.markdown(raw_description, extensions=['tables'])
    preview_desc = markdown.markdown(raw_preview, extensions=['tables'])
    full_desc = full_desc.replace('<table>', '<table class="table table-bordered table-striped">')
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}

    tags = []
    raw_tags = course_attr(course, 'tag')
    if raw_tags:
        try:
            tags = ast.literal_eval(raw_tags)
        except (ValueError, SyntaxError, TypeError):
            if isinstance(raw_tags, str):
                tags = [raw_tags]

    teacher_name = course_attr(course, 'Teacher', 'teacher')
    if teacher_name:
        tags.append(teacher_name)

    if 'همه آموزش ها' in tags:
        tags.remove('همه آموزش ها')
    tags = list(dict.fromkeys(tags))

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
            'certificate': course_attr(course, 'certificate', default=False),
            'cta': cta,
            'meta': meta,
            'canonical_url': course_public_url(course, external=True),
            'menu': category_menu,
            'tags': tags
            }
    return render_template('example.html', data=data)


@app.get('/api/s/<query>/')
@app.get('/api/s/<query>')
def search(query):
    start = time.time()
    regex = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)

    course_class = get_course_class()
    if course_class == Course:
        course_results = course_class.objects(
            __raw__={"$text": {"$search": query}}
        ).only("title", "course_id", "website", "course_url_name").limit(20)
    else:
        course_results = course_class.objects(
            __raw__={"$or": [
                {"title": regex},
                {"teacher": regex},
                {"description": regex},
                {"summary": regex},
                {"search_text": regex},
            ]}
        ).only("title", "course_id", "website", "course_url_name").limit(20)

    # 2. Match descriptions via regex from OptimizedCourse
    desc_matches = OptimizedCourse.objects.filter(
        short_description=regex
    ).only('course_id', 'website')

    matched_ids = set((str(desc.course_id), desc.website) for desc in desc_matches)

    # 3. Fetch extra courses based on matched_ids
    extra_courses = []
    if matched_ids:
        or_conditions = [{"course_id": {"$in": _course_id_variants(cid)}, "website": site} for cid, site in matched_ids]
        extra_courses = course_class.objects.filter(__raw__={"$or": or_conditions}).only("title", "course_id", "website", "course_url_name")

    # 4. Combine and deduplicate results
    combined = list(course_results) + list(extra_courses)
    unique_courses = {}
    for c in combined:
        key = (c.course_id, c.website)
        if key not in unique_courses:
            unique_courses[key] = c

    # 5. Build JSON response
    response = [{
        "title": c.title,
        "url": course_public_url(c)
    } for c in unique_courses.values()]

    print(f"Query time: {time.time() - start:.2f} seconds")
    return jsonify(response)




@app.route('/search/<query>')
def full_results(query):
    start = time.time()
    regex = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)
    course_class = get_course_class()

    # -----------------------------
    # 1. LIGHT SEARCH (fast, minimal fields)
    # -----------------------------
    search_ids = set()

    # 1A. text search on main course
    if course_class == Course:
        text_matches = course_class.objects(
            __raw__={"$text": {"$search": query}}
        ).only("title", "course_id", "website")  # minimal fields for speed
    else:
        text_matches = course_class.objects(
            __raw__={"$or": [
                {"title": regex},
                {"teacher": regex},
                {"description": regex},
                {"summary": regex},
                {"search_text": regex},
            ]}
        ).only("title", "course_id", "website")

    for c in text_matches:
        search_ids.add((str(c.course_id), c.website))

    # 1B. regex search in OptimizedCourse.short_description
    desc_matches = OptimizedCourse.objects(short_description=regex).only("course_id", "website")
    for d in desc_matches:
        search_ids.add((str(d.course_id), d.website))

    # 1C. regex search on lightweight fields
    name_search_field = 'Teacher' if course_class == Course else 'teacher'
    regex_matches = course_class.objects(
        __raw__={"$or": [
            {"title": regex},
            {name_search_field: regex},
        ]}
    ).only("course_id", "website")

    for r in regex_matches:
        search_ids.add((str(r.course_id), r.website))

    # -----------------------------
    # 2. FETCH FULL COURSE INFO (heavy fields)
    # -----------------------------
    if search_ids:
        or_conditions = [{"course_id": {"$in": _course_id_variants(cid)}, "website": site} for cid, site in search_ids]
        full_courses = course_class.objects(__raw__={"$or": or_conditions})
    else:
        full_courses = []

    # -----------------------------
    # 3. Pagination
    # -----------------------------
    all_courses = list(full_courses)
    count = len(all_courses)
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 20))
    pages_count = ceil(count / page_size)

    # Sort by discount and slice for pagination
    sorted_courses = sorted(
                        all_courses,
                        key=course_score,
                        reverse=True
                    )
    posts = sorted_courses[(page - 1) * page_size: page * page_size]

    # Pagination navigation
    previous_pages = list(range(1, page))
    next_pages = list(range(page, pages_count + 1))
    pages = previous_pages[-2:] + next_pages[:3]

    # Build pagination URLs
    page_urls = {}
    all_needed_pages = set(pages + [1, pages_count])
    for i in all_needed_pages:
        page_urls[i] = url_for('full_results', query=query, page=i, page_size=page_size)

    # -----------------------------
    # 4. Category menu and render
    # -----------------------------
    categories = Category.objects
    category_menu = {i.title: i.name for i in categories}

    data = {
        'keywords': [query],
        'menu': category_menu,
        'posts': posts,
        'pages': pages,
        'current_page': page,
        'last_page': pages_count,
        'page_urls': page_urls,
    }

    print(f"Query time: {time.time() - start} seconds")

    return render_template("search_results.html", courses=posts, query=query, data=data)



if __name__ == '__main__':
    app.run(debug=True)
