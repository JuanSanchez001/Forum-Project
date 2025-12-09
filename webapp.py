from flask import Flask, redirect, url_for, session, request, render_template
from flask_oauthlib.client import OAuth
import pymongo
import os
import pprint
from bson.objectid import ObjectId
from datetime import datetime

app = Flask(__name__)

app.debug = False
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # REMOVE IN PRODUCTION

app.secret_key = os.environ['SECRET_KEY']
oauth = OAuth(app)
oauth.init_app(app)

# Configure GitHub OAuth
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'],
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],
    request_token_params={'scope': 'user:email'},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)

# MongoDB setup
connection_string = os.environ["MONGO_CONNECTION_STRING"]
db_name = os.environ["MONGO_DBNAME"]

client = pymongo.MongoClient(connection_string)
db = client[db_name]
collection = db['Post']

try:
    client.admin.command('ping')
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print("❌ MongoDB connection failed:", e)

@app.context_processor
def inject_logged_in():
    is_logged_in = 'github_token' in session
    return {"logged_in": is_logged_in}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http'))

@app.route('/logout')
def logout():
    session.clear()
    return render_template('message.html', message='You were logged out.')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args.get('error', '') + ' description=' + request.args.get('error_description', '')
    else:
        try:
            session['github_token'] = (resp['access_token'], '')
            session['user_data'] = github.get('user').data
            message = f"You were successfully logged in as {session['user_data']['login']}."
            return redirect(url_for('list_posts'))
        except Exception as e:
            session.clear()
            message = f"Unable to login: {e}"
    return render_template('message.html', message=message)

@app.route('/page1', methods=['GET', 'POST'])
def renderPage1():
    if 'github_token' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        user = session['user_data']
        post = {
            "title": request.form['title'],
            "content": request.form['content'],
            "author": {
                "username": user['login'],
                "github_id": user['id']
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "views": 0,
            "is_published": True
        }
        collection.insert_one(post)
        return redirect(url_for('list_posts'))

    return render_template('page1.html')

@app.route('/posts')
def list_posts():
    posts = list(collection.find().sort("created_at", -1))
    return render_template('posts.html', posts=posts)

@app.route('/post/<post_id>')
def view_post(post_id):
    post = collection.find_one({"_id": ObjectId(post_id)})
    if post:
        collection.update_one({"_id": ObjectId(post_id)}, {"$inc": {"views": 1}})
        post['views'] += 1
        return render_template('view_post.html', post=post)
    return render_template('message.html', message="Post not found.")

@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')

if __name__ == '__main__':
    app.run(debug=True)
