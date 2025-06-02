from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired, NumberRange
import requests, os

API_KEY = os.environ.get('API_KEY')
SESSION_ID = os.environ.get('SESSION_ID')

headers = {
    'accept': 'application/json',
    'content-type': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
}

class EditForm(FlaskForm):
    new_rating = FloatField(label = 'Your rating out of 10', validators = [DataRequired(), NumberRange(0, 10)])
    new_review = StringField(label = 'Your review')
    submit = SubmitField(label = 'Done')

app = Flask(__name__, instance_relative_config=True)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
Bootstrap5(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies-collection.db'
# CREATE DB
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class = Base)
db.init_app(app)

class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key = True)
    title: Mapped[str] = mapped_column(String(250), unique = True, nullable = False)
    year: Mapped[str] = mapped_column(String, nullable = False)
    description: Mapped[str] = mapped_column(String, nullable = False)
    rating: Mapped[float] = mapped_column(Float, nullable = True)
    ranking: Mapped[int] = mapped_column(Integer, nullable = True)
    review: Mapped[str] = mapped_column(String, nullable = True)
    img_url: Mapped[str] = mapped_column(String, nullable = False)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating.desc())).scalars().all()
    for i, movie in enumerate(result):
        movie.ranking = i + 1
    db.session.commit()
    movies = db.session.execute(db.select(Movie).order_by(Movie.ranking.desc())).scalars().all()
    return render_template("index.html", movies = movies)

@app.route('/edit', methods = ['POST', 'GET'])
def edit():
    form = EditForm()
    movie_id = request.args.get('id', type = int)
    movie_to_update = db.session.execute(db.select(Movie).where(Movie.id == movie_id)).scalar()

    if form.validate_on_submit():
        movie_to_update.rating = form.new_rating.data
        movie_to_update.review = form.new_review.data or movie_to_update.review
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', form = form, movie = movie_to_update)

@app.route('/delete', methods = ['GET'])
def delete():
    movie_id = request.args.get('id', type = int)
    movie_to_delete = db.get_or_404(Movie, movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/add')
def add():
    return render_template('add.html')

@app.route('/select-movie', methods = ['POST', 'GET'])
def select():
    movie_name = request.form['movie-title']
    body = {
        'query': movie_name
    }
    response = requests.get('https://api.themoviedb.org/3/search/movie', params = body, headers = headers)
    movies = response.json()['results']
    return render_template('select.html', movies = movies)

@app.route('/find-movie')
def find():
    movie_id = request.args.get('id_json')
    movie_info = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}', headers = headers).json()
    movie_title = movie_info['title']
    year = movie_info['release_date']
    description = movie_info['overview']
    img_url = f"https://image.tmdb.org/t/p/w500{movie_info['poster_path']}"
    new_movie = Movie(title = movie_title, year = year, description = description,img_url = img_url)
    db.session.add(new_movie)
    db.session.commit()
    return redirect(url_for('edit', id = new_movie.id))

if __name__ == '__main__':
    app.run()
