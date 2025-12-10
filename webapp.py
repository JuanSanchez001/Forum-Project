from flask import Flask, redirect, url_for, session, request, jsonify, request
from flask_oauthlib.client import OAuth
#from flask_oauthlib.contrib.apps import github #import to make requests to GitHub's OAuth
from flask import render_template

import pprint
import os
import pymongo
import sys
from bson.objectid import ObjectId
from datetime import datetime

# This code originally from https://github.com/lepture/flask-oauthlib/blob/master/example/github.py
# Edited by P. Conrad for SPIS 2016 to add getting Client Id and Secret from
# environment variables, so that this will work on Heroku.
# Edited by S. Adams for Designing Software for the Web to add comments and remove flash messaging

app = Flask(__name__)

app.debug = False #Change this to False for production
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #Remove once done debugging, REMOVE WHEN ON RENDER ig

app.secret_key = os.environ['SECRET_KEY'] #used to sign session cookies
oauth = OAuth(app)
oauth.init_app(app) #initialize the app to be able to make requests for user information

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key=os.environ['GITHUB_CLIENT_ID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

connection_string = os.environ["MONGO_CONNECTION_STRING"]
db_name = os.environ["MONGO_DBNAME"]
    
client = pymongo.MongoClient(connection_string)
db = client[db_name]
collection = db['Post'] #1. put the name of your collection in the quotes
     # Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary 
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    is_logged_in = 'github_token' in session #this will be true if the token is in the session and false otherwise
    return {"logged_in":is_logged_in}

@app.route('/')
def home():
    return render_template('home.html')

#redirect to GitHub's OAuth page and confirm callback URL
@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='http')) #callback URL must match the pre-configured callback URL

@app.route('/logout')
def logout():
    session.clear()
    return render_template('message.html', message='You were logged out')

@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args)      
    else:
        try:
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            #session['test']=request.form['test']
            message='You were successfully logged in as ' + session['user_data']['login'] + '.'
            return redirect(url_for('list_posts'))
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
    return render_template('message.html', message=message)

@app.route('/page1', methods=['GET', 'POST'])
def renderPage1():
    if request.method == 'POST':
        user = session['user_data']
        post = {
                "title": request.form['title'],
                "content": request.form['content'], 
                "username": user['login'],
                "created_at" : datetime.now(),
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
    return render_template('view_post.html', post=post)
    return render_template('message.html', message="Post not found.")
'''@app.route('/post/<post_id>')
def view_post(post_id):
    post = collection.find_one({"_id": ObjectId(post_id)})
    if post:
        collection.update_one({"_id": ObjectId(post_id)}, {"$inc": {"views": 1}})
        post['views'] += 1
        return render_template('view_post.html', post=post)
    return render_template('message.html', message="Post not found.")'''



#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session['github_token']


if __name__ == '__main__':
    app.run(debug=True)
    

'''
ex.{
  "_id": ObjectId("60d5ec49f7e5f3a9e3d4f1c1"),
  "title": "How to design a schema for forum posts in MongoDB?",
  "content": "I'm building a forum and need help with the data model. What are the best practices for storing posts and comments?",
  "author": {
    "user_id": ObjectId("5099803df3f4948bd2f98391"),
    "username": "MongoDB_User"
  },
  "category": "Schema Design",
  "tags": ["data modeling", "best practices", "forum"],
  "views": 1250000,
  "created_at": ISODate("2025-12-05T12:00:00Z"),
  "updated_at": ISODate("2025-12-05T12:30:00Z"),
  "is_published": true,
  "comments_count": 42
}
'''

'''Start of project

make github repo, add starter code, connect with mongodb through python, make code from like mongodb practice make dictionarys in this cas 'posts'. Example above.
Goal is to allow a user to make something similar above. responses from a user are collected through dictionaries and sent to mongodb atlas where they are in a 
database  collection and document.'''

''''''
    
'''
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

    return render_template('page1.html')'''    