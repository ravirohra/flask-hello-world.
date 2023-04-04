import datetime

from flask import Flask, render_template, redirect, url_for, flash,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from functools import wraps

import forms
from forms import CreatePostForm
from flask_gravatar import Gravatar



app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.__init__(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

@login_manager.user_loader
def load_user(usr_id):
    return db.session.query(User).get(usr_id)


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

##CONFIGURE TABLES
with app.app_context():
    class BlogPost(db.Model):
        __tablename__ = "blog_posts"
        id = db.Column(db.Integer, primary_key=True)
        author = relationship('User',back_populates='blog_post')
        author_id=db.Column(db.Integer,db.ForeignKey('user.id'))
        title = db.Column(db.String(250), unique=True, nullable=False)
        subtitle = db.Column(db.String(250), nullable=False)
        date = db.Column(db.String(250), nullable=False)
        body = db.Column(db.Text, nullable=False)
        img_url = db.Column(db.String(250), nullable=False)
        comment=relationship('Comment',back_populates='parent_post')

    class User(db.Model, UserMixin):
        __tablename__ = "user"
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String, nullable=False)
        password = db.Column(db.String, nullable=False)
        name = db.Column(db.String, nullable=False)
        blog_post=relationship('BlogPost',back_populates='author')
        comments=relationship('Comment',back_populates='users')
    class Comment(db.Model):
        __tablename__='comments'
        id=db.Column(db.Integer,primary_key=True)
        text=db.Column(db.String,nullable=False)
        user_id=db.Column(db.Integer,db.ForeignKey('user.id'))
        users=relationship('User',back_populates='comments')
        post_id=db.Column(db.Integer,db.ForeignKey('blog_posts.id'))
        parent_post=relationship('BlogPost',back_populates='comment')

    db.create_all()


# def only_admin(fun):
#     # @app.errorhandler(403)
#     # @wraps(fun)
#     # def ok(fun):
#     #     return fun
#     # if current_user.id!=1:
#     #     return ok
#     # else:
#     #     return abort(403)
def admin_only(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # If id is not 1 then return abort with 403 error
            try:
                if current_user.id != 1:
                    flash('you are not do that')
                    posts = BlogPost.query.all()
                    return render_template("index.html", all_posts=posts, aut=current_user.is_authenticated)
            except AttributeError:
                flash('try login or sign first')
                return redirect('/')
            # Otherwise continue with the route function
            return f(*args, **kwargs)

        return decorated_function

@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,aut=current_user.is_authenticated)


@app.route('/register',methods=['get','post'])
def register():
    regester = forms.Regista()
    if regester.validate_on_submit():
        with app.app_context():
            ema=db.session.query(User).filter_by(email=regester.email.data).first()
            if not ema:
                new_user=User(email=regester.email.data,
                                  password=generate_password_hash(password=regester.password.data),
                                  name=regester.user_name.data)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect('/')
            else:
                flash('Email is already exits try different one or try login ',category='email')



    return render_template("register.html", form=regester,aut=current_user.is_authenticated)


@app.route('/login',methods=['get','post'])
def login():
    login=forms.Login_form()
    if login.validate_on_submit():
        with app.app_context():
            email=db.session.query(User).filter_by(email=login.email.data).first()
            if email:
                if check_password_hash(pwhash=email.password,password=login.password.data):
                    login_user(email)
                    return redirect('/')
                else:
                    flash("wrong password try again",category='password')
            else:
                flash("email is wrong or try to sign in fist",category="email")

    return render_template("login.html",form=login,aut=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['get','post'])
def show_post(post_id):
    with app.app_context():
        requested_post = BlogPost.query.get(post_id)
        at=BlogPost.query.get(post_id).author.name
        comment=forms.Comment()


        if comment.validate_on_submit():
            new_comment=Comment(
                text=comment.comment.data,
                user_id=current_user.id,
                post_id=post_id
            )
            db.session.add(new_comment)
            db.session.commit()
        return render_template("post.html", post=requested_post,aut=current_user.is_authenticated,at=at,comment=comment,g=gravatar)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=['get','post'])
@admin_only
def add_new_post():
        new_post = CreatePostForm()
        if new_post.validate_on_submit():
            with app.app_context():
                db.session.add(BlogPost(
                    title=new_post.title.data,
                    date=datetime.datetime.now().strftime("%B %d, %Y"),
                    body=new_post.body.data,
                    author_id=current_user.id,
                    img_url=new_post.img_url.data,
                    subtitle=new_post.subtitle.data
                ))
                db.session.commit()
            return redirect("/")

        return render_template('make-post.html', form=new_post, o="n")


@app.route("/edit-post/<int:post_id>",methods=['get','post'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        with app.app_context():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = edit_form.author.data
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>",methods=['get','post'])
@admin_only
def delete_post(post_id):
    with app.app_context():
        post_to_delete = BlogPost.query.get(post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
