from flask import Flask, render_template, request, redirect, url_for
from flask import request
from datetime import datetime, time
from flask import flash


app = Flask(__name__)

# Обновленное меню с напитками
menu = [
    {
        "id": 1,
        "name": "Стейк Рибай",
        "price": 1200,
        "category": "Горячие блюда",
        "image": "dish1.jpg"
    },
    {
        "id": 2,
        "name": "Салат Цезарь",
        "price": 450,
        "category": "Салаты",
        "image": "dish2.jpg"
    },
    {
        "id": 3,
        "name": "Тирамису",
        "price": 350,
        "category": "Десерты",
        "image": "dish3.jpg"
    },
    {
        "id": 4,
        "name": "Кола",
        "price": 150,
        "category": "Напитки",
        "image": "dish1.jpg"
    },
    {
        "id": 5,
        "name": "Кофе",
        "price": 200,
        "category": "Напитки",
        "image": "dish2.jpg"
    },
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/menu')
def show_menu():
    category = request.args.get('category')
    filtered_menu = menu
    if category:
        filtered_menu = [item for item in menu if item['category'].lower() == category.lower()]
    return render_template('menu.html', menu=filtered_menu, category=category)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/reservation', methods=['GET', 'POST'])
def reservation():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        guests = request.form['guests']
        date_str = request.form['date']
        time_str = request.form['time']

        # Валидация времени
        try:
            booking_time = datetime.strptime(time_str, '%H:%M').time()
            start_time = time(10, 0)
            end_time = time(23, 0)

            if not (start_time <= booking_time <= end_time):
                flash('Ресторан работает с 10:00 до 23:00. Выберите время в этом интервале.')
                return redirect(url_for('reservation'))

        except ValueError:
            flash('Некорректный формат времени')
            return redirect(url_for('reservation'))

        # Валидация даты
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d')
            if booking_date.date() < datetime.now().date():
                flash('Нельзя забронировать столик на прошедшую дату')
                return redirect(url_for('reservation'))
        except ValueError:
            flash('Некорректный формат даты')
            return redirect(url_for('reservation'))

        # Редирект с параметрами
        return redirect(url_for('reservation_success',
                                name=name,
                                date=date_str,
                                time=time_str,
                                guests=guests))

    return render_template('reservation.html')


@app.route('/reservation/success')
def reservation_success():
    return render_template('reservation_success.html',
                           name=request.args.get('name'),
                           date=request.args.get('date'),
                           time=request.args.get('time'),
                           guests=request.args.get('guests'))


if __name__ == '__main__':
    app.run(debug=True)
