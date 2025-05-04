from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import *
import requests
from flask_caching import Cache

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация расширений
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
cache.init_app(app)

# Конфигурация Яндекс.Карт
YANDEX_MAPS_API_KEY = 'f3a0fe3a-b07e-4840-a1da-06f18b2ddf13'
MAPS_BASE_URL = 'https://static-maps.yandex.ru/v1'

# Данные для генерации контента
PROMO_DATA = [
    {'image': 'banner1.jpg', 'title': 'Специальное предложение!', 'text': 'Скидка 20% на все основные блюда'},
    {'image': 'banner2.jpg', 'title': 'Новые десерты', 'text': 'Попробуйте наши сезонные десерты'},
    {'image': 'banner3.jpg', 'title': 'Вино дня', 'text': 'Отборные вина со скидкой 30%'}
]

MENU_CATEGORIES = [
    {'id': 'Горячие блюда', 'title': 'Основные блюда', 'image': 'main-dishes.jpg'},
    {'id': 'Напитки', 'title': 'Напитки', 'image': 'drinks.jpg'},
    {'id': 'Десерты', 'title': 'Десерты', 'image': 'desserts.jpg'}
]

MENU_ITEMS = {
    'Напитки': [
        {'title': 'Зеленый чай', 'price': 150, 'image': 'green_tea.jpg'},
        {'title': 'Черный чай', 'price': 150, 'image': 'black_tea.jpg'},
        {'title': 'Вишневый лимонад', 'price': 250, 'image': 'cherry_lemonade.jpg'},
        {'title': 'Клубничный лимонад', 'price': 250, 'image': 'strawberry_lemonade.jpg'},
        {'title': 'Пиноколада', 'price': 350, 'image': 'pina_colada.jpg'}
    ],
    'Горячие блюда': [
        {'title': 'Филе утиной грудки', 'price': 790, 'image': 'duck.jpg'},
        {'title': 'Шашлык из свиной шеи', 'price': 650, 'image': 'shashlik.jpg'},
        {'title': 'Филе трески', 'price': 720, 'image': 'cod.jpg'},
        {'title': 'Греческий салат', 'price': 450, 'image': 'greek_salad.jpg'},
        {'title': 'Цезарь с курицей', 'price': 480, 'image': 'caesar_chicken.jpg'},
        {'title': 'Цезарь с креветкой', 'price': 550, 'image': 'caesar_shrimp.jpg'}
    ],
    'Десерты': [
        {'title': 'Тирамису', 'price': 320, 'image': 'tiramisu.jpg'},
        {'title': 'Наполеон', 'price': 300, 'image': 'napoleon.jpg'},
        {'title': 'Яблочный штрудель', 'price': 280, 'image': 'shtrudel.jpg'}
    ]
}
RESERVATION_CONFIG = {
    'working_hours': {
        'min_time': '10:00',
        'max_time': '22:30',
        'days_ahead': 30  # Максимальное дней для бронирования вперед
    },
    'guests_options': list(range(1, 11)),
    'phone_pattern': r'\+7\s?[0-9]{3}\s?[0-9]{3}\s?[0-9]{2}\s?[0-9]{2}',
    'success_message': {
        'title': 'Бронирование подтверждено!',
        'text': 'Ждем вас в указанное время',
        'icon': 'bi-check-circle'
    }
}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    reservations = db.relationship('Reservation', backref='user', lazy=True)

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)
    guest_phone = db.Column(db.String(20), nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    guests = db.Column(db.Integer, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Маршруты
@app.route('/')
def home():
    return render_template('index.html',
                         title='Главная',
                         promo_data=PROMO_DATA,
                         categories=MENU_CATEGORIES)

@app.route('/menu')
def show_menu():
    category = request.args.get('category', 'Горячие блюда')
    return render_template('menu.html',
                         title='Меню',
                         menu_items=MENU_ITEMS.get(category, []),
                         categories=MENU_CATEGORIES,
                         current_category=category)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    # Обработка POST-запроса (форма обратной связи)
    if request.method == 'POST':
        if current_user.is_authenticated:
            name = current_user.name
            email = current_user.email
        else:
            name = request.form.get('name')
            email = request.form.get('email')
            if not name or not email:
                flash('Заполните все обязательные поля', 'danger')
                return redirect(url_for('contact'))

        message = request.form.get('message')
        if not message:
            flash('Введите текст сообщения', 'danger')
            return redirect(url_for('contact'))

        flash('Сообщение успешно отправлено!', 'success')
        return redirect(url_for('contact'))

    # Генерация карты для GET-запроса
    restaurant_lon = 31.384180
    restaurant_lat = 58.426373

    map_url = generate_map_url(
        lon=restaurant_lon,
        lat=restaurant_lat,
        zoom=16,
        size='1000x600'
    )

    return render_template('contact.html',
                           map_url=map_url,
                           title='Контакты')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, phone=phone, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Регистрация успешна! Теперь войдите', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Ошибка регистрации', 'danger')

    return render_template('register.html', title='Регистрация')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('profile'))
        flash('Неверные данные', 'danger')
    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    current_date = datetime.now().strftime('%Y-%m-%d')
    max_date = (datetime.now() + timedelta(days=RESERVATION_CONFIG['working_hours']['days_ahead'])).strftime('%Y-%m-%d')

    if request.method == 'POST':
        try:
            date_str = request.form['date']
            time_str = request.form['time']
            guests = int(request.form['guests'])
            booking_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

            if not (time(10, 0) <= booking_time.time() <= time(23, 0)):
                flash('Вне времени работы', 'danger')
                return redirect(url_for('reservation'))

            if current_user.is_authenticated:
                reservation = Reservation(
                    user_id=current_user.id,
                    date=booking_time,
                    guests=guests
                )
            else:
                reservation = Reservation(
                    guest_name=request.form['name'],
                    guest_email=request.form['email'],
                    guest_phone=request.form['phone'],
                    date=booking_time,
                    guests=guests
                )

            db.session.add(reservation)
            db.session.commit()
            return redirect(url_for('reservation_success'))

        except Exception as e:
            db.session.rollback()
            flash('Ошибка бронирования', 'danger')

    return render_template('reservation.html',
                           title='Бронирование',
                           current_date=current_date,
                           max_date=max_date,
                           config=RESERVATION_CONFIG)

    @app.route('/reservation/success')
    def reservation_success():
        return render_template('reservation_success.html',
                               title='Успешное бронирование',
                               config=RESERVATION_CONFIG)

@app.route('/profile')
@login_required
def profile():
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(
        Reservation.date.desc()
    ).all()
    return render_template('profile.html',
                           title='Профиль',
                           user=current_user,
                           reservations=reservations)


@cache.memoize(timeout=3600)
def generate_map_url(lon: float, lat: float, zoom: int = 15, size: str = '650,450') -> str:
    try:
        # Проверка и нормализация параметров
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise ValueError("Некорректные координаты")

        # Проверка допустимых размеров
        if size not in ['450,450', '650,450', '450,650']:
            size = '650,450'

        params = {
            'll': f'{lon},{lat}',
            'z': min(max(zoom, 0), 17),  # Ограничение зума
            'size': size,
            'pt': f'{lon},{lat},vkbkm',  # Измененный тип метки
            'apikey': YANDEX_MAPS_API_KEY,
            'l': 'map'  # Явное указание типа карты
        }

        response = requests.get(MAPS_BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        return response.url

    except (requests.exceptions.RequestException, ValueError) as e:
        app.logger.error(f"Ошибка генерации карты: {str(e)}")
        return None


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)