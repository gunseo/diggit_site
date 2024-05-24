from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)

# Generate a random secret key for production
app.config['SECRET_KEY'] = os.urandom(24)

# Or, use a fixed secret key for development (less secure)
# app.config['SECRET_KEY'] = 'your_very_secret_key'

# SQLite database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    items = db.relationship('Item', foreign_keys='Item.user_id', backref='owner', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    image = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    current_bid = db.Column(db.Float, nullable=True)
    buy_now_price = db.Column(db.Float, nullable=False)
    bidder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    bidder = db.relationship('User', foreign_keys=[bidder_id], backref='bids')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Login Unsuccessful. Please check your credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    items = Item.query.all()
    return render_template('index.html', items=items)

@app.route('/item/<int:item_id>')
@login_required
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    return render_template('item_detail.html', item=item)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        image = request.files['image']
        end_time = datetime.strptime(request.form.get('end_time'), '%Y-%m-%dT%H:%M')
        buy_now_price = float(request.form.get('buy_now_price'))
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_item = Item(name=name, description=description, image=filename, end_time=end_time, buy_now_price=buy_now_price, user_id=current_user.id)
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('upload.html')

@app.route('/bid/<int:item_id>', methods=['POST'])
@login_required
def bid(item_id):
    item = Item.query.get_or_404(item_id)
    bid_amount = float(request.form.get('bid_amount'))
    
    if bid_amount > (item.current_bid or 0) and bid_amount < item.buy_now_price:
        item.current_bid = bid_amount
        item.bidder_id = current_user.id
        db.session.commit()
        flash(f'Successfully placed a bid of {bid_amount} on {item.name}')
    elif bid_amount >= item.buy_now_price:
        item.current_bid = item.buy_now_price
        item.bidder_id = current_user.id
        db.session.commit()
        flash(f'You have bought {item.name} at the buy now price of {item.buy_now_price}')
    else:
        flash('Your bid must be higher than the current bid and lower than the buy now price.')

    return redirect(url_for('index'))

@app.route('/buy_now/<int:item_id>')
@login_required
def buy_now(item_id):
    item = Item.query.get_or_404(item_id)
    item.current_bid = item.buy_now_price
    item.bidder_id = current_user.id
    db.session.commit()
    flash(f'You have bought {item.name} at the buy now price of {item.buy_now_price}')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)