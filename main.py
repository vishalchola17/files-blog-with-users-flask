from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
# Import your forms from the forms.py
from forms import CreatePostForm, Register, Login, CommentForm
import os


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)

app.config['SECRET_KEY'] = "myblogwebsite"
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login


# TODO: create @admin_only decorator
def admin_only(fun):
    @wraps(fun)
    def wrapper(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return fun(*args, **kwargs)
    return wrapper

# CONNECT TO DB
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CONFIGURE TABLES\

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    comments = relationship("Comment", back_populates="comment_author")
    posts = relationship("BlogPost", back_populates="author")

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    comments = relationship("Comment", back_populates="parent_post")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")

    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")




# TODO: Create a User table for all your registered users. 



with app.app_context():
    db.create_all()


# TODO: Use Werkzeug to hash the user's password when creating a new user.



@app.route('/register', methods=["GET", "POST"])
def register():
    my_form = Register()
    if my_form.validate_on_submit():
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        result = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if result:
            flash("EMAIL ALREDY EXISTS")
            return redirect(url_for("login"))

        to_hash = generate_password_hash(password=password, salt_length=8, method='pbkdf2:sha256')

        to_add = User(name=name, email=email, password=to_hash)

        db.session.add(to_add)
        db.session.commit()

        return render_template("index.html")

    return render_template("register.html", form=my_form,current_user=current_user)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=["GET", "POST"])
def login():
    my_form = Login()
    if my_form.validate_on_submit():
        email_ = request.form.get("email")
        password = request.form.get("password")
        read = db.session.execute(db.select(User).where(User.email == email_)).scalar()

        if not read:
            flash("EMAIL DOES NOT MATCH OUR DATABASE, PLEASE CREATE NEW ACCOUNT")
            return redirect(url_for("register"))

        if check_password_hash(read.password, password) and read:
            login_user(read)
            return render_template("index.html")

        if not check_password_hash(read.password, password):
            flash("INVALID PASSWORD")
            return redirect(url_for("login"))
    return render_template("login.html", form=my_form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


# TODO: Allow logged-in users to comment on posts


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to register")
            return redirect(url_for("register"))
        new_comment = Comment(
            parent_post=requested_post,
            comment_author=current_user,
            text=form.comment_text.data
        )
        db.session.add(new_comment)
        db.session.commit()
        # return redirect(url_for("show_post", post_id=post_id))

    return render_template("post.html", post=requested_post, current_user=current_user, form=form)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

if __name__ == "__main__":
    app.run(debug=True, port=5002)
