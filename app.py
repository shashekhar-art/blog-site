import os
import glob
import math
import hmac
import re
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, abort, request, redirect, url_for, session, flash
import frontmatter
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from markdown.extensions.toc import TocExtension
from markdown.extensions.tables import TableExtension

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-prod')

POSTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'content', 'posts')
POSTS_PER_PAGE = 6

SITE_CONFIG = {
    'title': 'Shashi Shekhar Insights',
    'author': 'Shashi Shekhar',
    'description': 'Practical insights on Python, AI, Generative AI, Data Science & emerging technology',
    'url': 'https://shekhar-insight-blog.fly.dev',
    'linkedin': 'https://www.linkedin.com/in/shashi-shekhar-18octo/',
    'github': 'https://github.com/shashi-shekhar',
    'twitter': 'https://twitter.com/shashi_ai',
    'email': 'shashekhar@deloitte.com',
    'tagline': 'Exploring the Frontier of Generative AI',
}

ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'shashi')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'ShashiAdmin2026!')


# ── helpers ──────────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


def calculate_reading_time(content):
    words = len(content.split())
    minutes = max(1, math.ceil(words / 200))
    return minutes


def format_date(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d')
        except Exception:
            return dt
    return dt.strftime('%B %d, %Y')


app.jinja_env.filters['format_date'] = format_date


def get_all_posts():
    posts = []
    if not os.path.exists(POSTS_DIR):
        return posts

    for post_path in sorted(glob.glob(os.path.join(POSTS_DIR, '*.md')), reverse=True):
        try:
            with open(post_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)

            slug = os.path.basename(post_path).replace('.md', '')
            content_html = markdown.markdown(
                post.content,
                extensions=[
                    CodeHiliteExtension(css_class='highlight', guess_lang=True),
                    FencedCodeExtension(),
                    TocExtension(baselevel=2),
                    TableExtension(),
                    'nl2br',
                    'attr_list',
                ]
            )

            date_val = post.get('date', datetime.now())
            if isinstance(date_val, str):
                try:
                    date_val = datetime.strptime(date_val, '%Y-%m-%d')
                except Exception:
                    pass

            posts.append({
                'slug': slug,
                'title': post.get('title', 'Untitled'),
                'date': date_val,
                'category': post.get('category', 'General'),
                'tags': post.get('tags', []),
                'summary': post.get('summary', ''),
                'cover_gradient': post.get('cover_gradient', 'gradient-1'),
                'cover_emoji': post.get('cover_emoji', '🤖'),
                'author': post.get('author', 'Shashi Shekhar'),
                'content': content_html,
                'raw_content': post.content,
                'reading_time': calculate_reading_time(post.content),
                'featured': post.get('featured', False),
            })
        except Exception as e:
            print(f"Error loading post {post_path}: {e}")

    return sorted(posts, key=lambda x: x['date'] if isinstance(x['date'], datetime) else datetime.now(), reverse=True)


def _save_post(existing_slug):
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    category = request.form.get('category', 'GenAI').strip()
    tags = [t.strip() for t in request.form.get('tags', '').split(',') if t.strip()]
    summary = request.form.get('summary', '').strip()
    cover_gradient = request.form.get('cover_gradient', 'gradient-1')
    cover_emoji = request.form.get('cover_emoji', '🤖').strip()
    featured = request.form.get('featured') == 'on'
    post_date = request.form.get('date', str(date.today()))

    if existing_slug:
        slug = existing_slug
    else:
        slug_base = f"{post_date}-{slugify(title)}"
        slug = slug_base
        i = 1
        while os.path.exists(os.path.join(POSTS_DIR, f'{slug}.md')):
            slug = f'{slug_base}-{i}'
            i += 1

    post_obj = frontmatter.Post(
        content,
        title=title,
        date=post_date,
        category=category,
        tags=tags,
        summary=summary,
        cover_gradient=cover_gradient,
        cover_emoji=cover_emoji,
        author='Shashi Shekhar',
        featured=featured,
    )

    post_path = os.path.join(POSTS_DIR, f'{slug}.md')
    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(frontmatter.dumps(post_obj))

    flash('Post saved successfully!', 'success')
    return redirect(url_for('post_detail', slug=slug))


# ── public routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    posts = get_all_posts()
    featured = next((p for p in posts if p.get('featured')), posts[0] if posts else None)
    recent = [p for p in posts if not p.get('featured')][:5]
    if featured and featured in recent:
        recent = [p for p in posts if p['slug'] != featured['slug']][:5]

    categories = {}
    for post in posts:
        cat = post['category']
        categories[cat] = categories.get(cat, 0) + 1

    all_tags = []
    for post in posts:
        all_tags.extend(post.get('tags', []))
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return render_template('index.html',
                           featured=featured,
                           recent=recent,
                           categories=categories,
                           popular_tags=popular_tags,
                           total_posts=len(posts),
                           site=SITE_CONFIG)


@app.route('/blog')
def blog():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    tag = request.args.get('tag', None)
    search = request.args.get('search', '').strip()

    all_posts = get_all_posts()
    posts = all_posts[:]

    if category:
        posts = [p for p in posts if p['category'].lower() == category.lower()]
    if tag:
        posts = [p for p in posts if tag.lower() in [t.lower() for t in p.get('tags', [])]]
    if search:
        sl = search.lower()
        posts = [p for p in posts if sl in p['title'].lower() or sl in p['summary'].lower() or sl in p['raw_content'].lower()]

    total = len(posts)
    total_pages = max(1, math.ceil(total / POSTS_PER_PAGE))
    page = min(page, total_pages)
    start = (page - 1) * POSTS_PER_PAGE
    paginated = posts[start:start + POSTS_PER_PAGE]

    categories = {}
    for post in all_posts:
        cat = post['category']
        categories[cat] = categories.get(cat, 0) + 1

    all_tags = []
    for post in all_posts:
        all_tags.extend(post.get('tags', []))
    tag_counts = {}
    for t in all_tags:
        tag_counts[t] = tag_counts.get(t, 0) + 1
    popular_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:12]

    return render_template('blog.html',
                           posts=paginated,
                           page=page,
                           total_pages=total_pages,
                           total=total,
                           category=category,
                           tag=tag,
                           search=search,
                           categories=categories,
                           popular_tags=popular_tags,
                           site=SITE_CONFIG)


@app.route('/post/<slug>')
def post_detail(slug):
    posts = get_all_posts()
    current = None
    current_idx = None

    for i, p in enumerate(posts):
        if p['slug'] == slug:
            current = p
            current_idx = i
            break

    if not current:
        abort(404)

    prev_post = posts[current_idx + 1] if current_idx + 1 < len(posts) else None
    next_post = posts[current_idx - 1] if current_idx > 0 else None
    related = [p for p in posts if p['slug'] != slug and p['category'] == current['category']][:3]

    return render_template('post.html',
                           post=current,
                           prev_post=prev_post,
                           next_post=next_post,
                           related=related,
                           site=SITE_CONFIG)


@app.route('/about')
def about():
    return render_template('about.html', site=SITE_CONFIG)


@app.route('/category/<category>')
def category_view(category):
    return redirect(url_for('blog', category=category))


# ── admin routes ──────────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        if hmac.compare_digest(u, ADMIN_USER) and hmac.compare_digest(p, ADMIN_PASS):
            session.permanent = True
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = 'Invalid username or password.'
    return render_template('admin/login.html', error=error, site=SITE_CONFIG)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    posts = get_all_posts()
    return render_template('admin/dashboard.html', posts=posts, site=SITE_CONFIG)


@app.route('/admin/new', methods=['GET', 'POST'])
@admin_required
def admin_new():
    if request.method == 'POST':
        return _save_post(None)
    return render_template('admin/editor.html', post=None, site=SITE_CONFIG)


@app.route('/admin/edit/<slug>', methods=['GET', 'POST'])
@admin_required
def admin_edit(slug):
    post_path = os.path.join(POSTS_DIR, f'{slug}.md')
    if not os.path.exists(post_path):
        abort(404)
    if request.method == 'POST':
        return _save_post(slug)
    with open(post_path, 'r', encoding='utf-8') as f:
        p = frontmatter.load(f)
    post_data = {
        'slug': slug,
        'title': p.get('title', ''),
        'date': str(p.get('date', date.today())),
        'category': p.get('category', 'GenAI'),
        'tags': ', '.join(p.get('tags', [])),
        'summary': p.get('summary', ''),
        'cover_gradient': p.get('cover_gradient', 'gradient-1'),
        'cover_emoji': p.get('cover_emoji', '🤖'),
        'featured': p.get('featured', False),
        'content': p.content,
    }
    return render_template('admin/editor.html', post=post_data, site=SITE_CONFIG)


@app.route('/admin/delete/<slug>', methods=['POST'])
@admin_required
def admin_delete(slug):
    post_path = os.path.join(POSTS_DIR, f'{slug}.md')
    if os.path.exists(post_path):
        os.remove(post_path)
        flash('Post deleted.', 'info')
    return redirect(url_for('admin_dashboard'))


# ── error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', site=SITE_CONFIG), 404


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
