import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from models import db, User, Category, Transaction, RegularTransaction
from services.category_service import CategoryService
from services.transaction_service import TransactionService
from services.regular_transaction_service import RegularTransactionService
from services.account_service import AccountService

# Создаём приложение Flask
app = Flask(__name__)

# Конфигурация
app.config['SECRET_KEY'] = 'your-secret-key-change-this-to-something-secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'finance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализируем базу данных
db.init_app(app)

# Создаём папку instance, если её нет
os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

# Создаём таблицы при первом запуске
with app.app_context():
    db.create_all()


# ----- ДЕКОРАТОР ДЛЯ ЗАЩИТЫ МАРШРУТОВ -----

def login_required(f):
    """Декоратор для проверки авторизации пользователя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, авторизуйтесь для доступа к этой странице', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def load_logged_in_user():
    """Загружаем пользователя в глобальный объект g для доступа в шаблонах"""
    g.user = None
    if 'user_id' in session:
        g.user = User.query.get(session['user_id'])


# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -----

def create_default_categories(user_id):
    """Создаёт набор категорий по умолчанию для нового пользователя"""
    default_categories = [
        ('Продукты', 'expense', '#FF6B6B'),
        ('Транспорт', 'expense', '#4ECDC4'),
        ('Коммунальные платежи', 'expense', '#45B7D1'),
        ('Развлечения', 'expense', '#96CEB4'),
        ('Здоровье', 'expense', '#FFEAA7'),
        ('Одежда', 'expense', '#FF9F43'),
        ('Кафе и рестораны', 'expense', '#EE5A24'),
        ('Зарплата', 'income', '#55EFC4'),
        ('Фриланс', 'income', '#81ECEC'),
        ('Подарки', 'income', '#FFD93D'),
        ('Инвестиции', 'income', '#A29BFE'),
    ]
    
    for order, (name, type, color) in enumerate(default_categories):
        category = Category(
            name=name,
            type=type,
            color=color,
            order=order,
            user_id=user_id
        )
        db.session.add(category)
    
    db.session.commit()


# ----- МАРШРУТЫ АВТОРИЗАЦИИ -----

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа в систему"""
    # Если пользователь уже авторизован, перенаправляем на главную
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session.clear()
            session['user_id'] = user.id
            flash(f'Добро пожаловать, {username}!', 'success')
            
            # Перенаправляем на страницу, которую пытались открыть, или на главную
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации нового пользователя"""
    # Если пользователь уже авторизован, перенаправляем на главную
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Валидация
        if not username or not password:
            flash('Пожалуйста, заполните все поля', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'danger')
            return render_template('register.html')
        
        # Проверка на сложность пароля
        if not any(c.isdigit() for c in password):
            flash('Пароль должен содержать хотя бы одну цифру', 'danger')
            return render_template('register.html')
        
        if not any(c.isalpha() for c in password):
            flash('Пароль должен содержать хотя бы одну букву', 'danger')
            return render_template('register.html')
        
        # Проверка уникальности логина
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'danger')
            return render_template('register.html')
        
        # Создаём пользователя
        user = User(username=username)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Создаём категории по умолчанию
            create_default_categories(user.id)
            
            flash('Регистрация успешно завершена! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при регистрации: {str(e)}', 'danger')
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('login'))


# ----- МАРШРУТЫ СТРАНИЦ -----

@app.route('/')
@login_required
def index():
    """Главная страница"""
    user_id = session['user_id']
    
    # Получаем статистику для текущего пользователя
    stats = TransactionService.get_stats(user_id)
    
    # Получаем последние 5 транзакций
    recent_transactions = Transaction.query.filter_by(user_id=user_id)\
        .order_by(Transaction.date.desc())\
        .limit(5)\
        .all()
    
    return render_template('index.html', stats=stats, recent_transactions=recent_transactions)


# ----- МАРШРУТЫ КАТЕГОРИЙ -----

@app.route('/categories')
@login_required
def categories_list():
    """Список всех категорий"""
    user_id = session['user_id']
    
    # Получаем фильтр из параметров URL
    filter_type = request.args.get('filter', 'all')
    
    # Получаем все категории текущего пользователя
    all_categories = CategoryService.get_all_categories(user_id)
    
    # Фильтруем по типу для отображения
    if filter_type == 'income':
        expense_categories = []
        income_categories = [cat for cat in all_categories if cat.type == 'income']
    elif filter_type == 'expense':
        expense_categories = [cat for cat in all_categories if cat.type == 'expense']
        income_categories = []
    else:  # 'all'
        expense_categories = [cat for cat in all_categories if cat.type == 'expense']
        income_categories = [cat for cat in all_categories if cat.type == 'income']
    
    return render_template(
        'categories/list.html',
        categories=all_categories,
        expense_categories=expense_categories,
        income_categories=income_categories,
        current_filter=filter_type
    )


@app.route('/categories/create', methods=['GET', 'POST'])
@login_required
def category_create():
    """Создание новой категории"""
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Получаем данные из формы
        name = request.form.get('name', '')
        type = request.form.get('type', 'expense')
        color = request.form.get('color', '#808080')
        monthly_limit = request.form.get('monthly_limit', '')
        
        # Преобразуем лимит
        if monthly_limit and monthly_limit.strip():
            monthly_limit = float(monthly_limit)
        else:
            monthly_limit = None

        # Вызываем сервис с user_id
        success, message, category = CategoryService.create_category(
            name=name,
            type=type,
            color=color,
            monthly_limit=monthly_limit,  # Добавляем лимит
            user_id=user_id
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('categories_list'))
        else:
            flash(message, 'danger')

    return render_template('categories/create.html')

@app.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def category_edit(id):
    """Редактирование категории"""
    user_id = session['user_id']
    category = CategoryService.get_category_by_id(id, user_id)

    if not category:
        flash('Категория не найдена', 'danger')
        return redirect(url_for('categories_list'))

    if request.method == 'POST':
        # Получаем данные из формы
        name = request.form.get('name', '')
        type = request.form.get('type', 'expense')
        color = request.form.get('color', '#808080')
        monthly_limit = request.form.get('monthly_limit', '')
        
        # Преобразуем лимит
        if monthly_limit and monthly_limit.strip():
            monthly_limit = float(monthly_limit)
        else:
            monthly_limit = None

        # Вызываем сервис (нужно будет обновить метод update_category в сервисе)
        success, message = CategoryService.update_category(
            category_id=id,
            name=name,
            type=type,
            color=color,
            monthly_limit=monthly_limit,  # добавь этот параметр
            user_id=user_id
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('categories_list'))
        else:
            flash(message, 'danger')

    return render_template('categories/edit.html', category=category)

@app.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def category_delete(id):
    """Удаление категории"""
    user_id = session['user_id']
    success, message = CategoryService.delete_category(id, user_id)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('categories_list'))


@app.route('/categories/<int:id>/move', methods=['POST'])
@login_required
def category_move(id):
    """Перемещение категории (изменение порядка)"""
    user_id = session['user_id']
    data = request.get_json()
    direction = data.get('direction')
    
    if direction not in ['up', 'down']:
        return jsonify({'success': False, 'message': 'Неверное направление'})
    
    success, message = CategoryService.move_category(id, direction, user_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message})


# ----- МАРШРУТЫ ТРАНЗАКЦИЙ -----

@app.route('/transactions')
@login_required
def transactions_list():
    """Список всех транзакций с фильтрацией"""
    user_id = session['user_id']
    
    # Получаем параметры фильтрации из запроса
    period = request.args.get('period', 'all')
    category_id = request.args.get('category')
    type_filter = request.args.get('type')
    
    # Преобразуем category_id в int, если он есть
    if category_id and category_id != 'all':
        try:
            category_id = int(category_id)
        except ValueError:
            category_id = None
    else:
        category_id = None
    
    # Получаем транзакции с фильтрацией
    transactions = TransactionService.get_transactions_filtered(
        user_id=user_id,
        period=period,
        category_id=category_id,
        type=type_filter if type_filter != 'all' else None
    )
    
    # Получаем все категории для фильтра
    categories = Category.query.filter_by(user_id=user_id).order_by(Category.type, Category.name).all()
    
    # Получаем статистику
    stats = TransactionService.get_stats(user_id)
    
    return render_template(
        'transactions/list.html',
        transactions=transactions,
        categories=categories,
        stats=stats
    )


@app.route('/transactions/create', methods=['GET', 'POST'])
@login_required
def transaction_create():
    """Создание новой транзакции"""
    user_id = session['user_id']
    
    if request.method == 'POST':
        # Получаем данные из формы
        type = request.form.get('type', 'expense')
        category_id = request.form.get('category_id', type=int)
        account_id = request.form.get('account_id', type=int)  # НОВЫЙ ПАРАМЕТР
        amount = request.form.get('amount', type=float)
        date_str = request.form.get('date')
        comment = request.form.get('comment', '')
        is_regular = request.form.get('is_regular') == 'on'
        
        # Преобразуем дату
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date = datetime.now()
        
        # Если это регулярная транзакция, создаем шаблон
        if is_regular:
            regular_name = request.form.get('regular_name', '')
            frequency = request.form.get('frequency', 'monthly')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else date
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
            
            success, message, regular = RegularTransactionService.create_regular_transaction(
                name=regular_name,
                amount=amount,
                category_id=category_id,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                comment=comment,
                type=type,
                user_id=user_id
            )
            
            if not success:
                flash(message, 'danger')
                return redirect(url_for('transaction_create', type=type))
        
        # Создаем обычную транзакцию с account_id
        success, message, transaction = TransactionService.create_transaction(
            amount=amount,
            date=date,
            category_id=category_id,
            account_id=account_id,  # ДОБАВЛЕН ПАРАМЕТР
            comment=comment,
            type=type,
            user_id=user_id
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('transactions_list'))
        else:
            flash(message, 'danger')
    
    # GET запрос
    categories = Category.query.filter_by(user_id=user_id).order_by(Category.type, Category.name).all()
    from models import Account
    accounts = Account.query.filter_by(user_id=user_id, is_active=True).all()
    type = request.args.get('type', 'expense')
    today = datetime.now().strftime('%Y-%m-%d')
    
    return render_template(
        'transactions/create.html',
        categories=categories,
        accounts=accounts,
        type=type,
        today=today
    )
@app.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def transaction_edit(id):
    """Редактирование транзакции"""
    user_id = session['user_id']
    transaction = TransactionService.get_transaction_by_id(id, user_id)
    
    if not transaction:
        flash('Транзакция не найдена', 'danger')
        return redirect(url_for('transactions_list'))
    
    if request.method == 'POST':
        # Получаем данные из формы
        category_id = request.form.get('category_id', type=int)
        account_id = request.form.get('account_id', type=int)  # НОВЫЙ ПАРАМЕТР
        amount = request.form.get('amount', type=float)
        date_str = request.form.get('date')
        comment = request.form.get('comment', '')
        
        # Преобразуем дату
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            date = transaction.date
        
        # Вызываем сервис с account_id
        success, message = TransactionService.update_transaction(
            transaction_id=id,
            amount=amount,
            date=date,
            category_id=category_id,
            account_id=account_id,  # ДОБАВЛЕН ПАРАМЕТР
            comment=comment,
            user_id=user_id
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('transactions_list'))
        else:
            flash(message, 'danger')
    
    # Получаем все категории и счета для формы
    categories = Category.query.filter_by(user_id=user_id).order_by(Category.type, Category.name).all()
    from models import Account
    accounts = Account.query.filter_by(user_id=user_id, is_active=True).all()
    
    return render_template(
        'transactions/edit.html',
        transaction=transaction,
        categories=categories,
        accounts=accounts  # ДОБАВЛЕНА ПЕРЕМЕННАЯ
    )

@app.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def transaction_delete(id):
    """Удаление транзакции"""
    user_id = session['user_id']
    success, message = TransactionService.delete_transaction(id, user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('transactions_list'))


# ----- МАРШРУТЫ РЕГУЛЯРНЫХ ТРАНЗАКЦИЙ -----

@app.route('/regular-transactions')
@login_required
def regular_transactions_list():
    """Список регулярных транзакций"""
    user_id = session['user_id']
    regulars = RegularTransactionService.get_all_regular_transactions(user_id)
    return render_template('regular_transactions/list.html', regulars=regulars)


@app.route('/regular-transactions/create', methods=['GET', 'POST'])
@login_required
def regular_transaction_create():
    """Создание регулярной транзакции"""
    user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        amount = request.form.get('amount', type=float)
        category_id = request.form.get('category_id', type=int)
        frequency = request.form.get('frequency', 'monthly')
        type = request.form.get('type', 'expense')
        comment = request.form.get('comment', '')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Преобразуем даты
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        success, message, regular = RegularTransactionService.create_regular_transaction(
            name=name,
            amount=amount,
            category_id=category_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            comment=comment,
            type=type,
            user_id=user_id
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('regular_transactions_list'))
        else:
            flash(message, 'danger')
    
    categories = Category.query.filter_by(user_id=user_id).order_by(Category.type, Category.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('regular_transactions/create.html', categories=categories, today=today)


@app.route('/regular-transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def regular_transaction_edit(id):
    """Редактирование регулярной транзакции"""
    user_id = session['user_id']
    regular = RegularTransactionService.get_regular_transaction_by_id(id, user_id)
    
    if not regular:
        flash('Регулярная транзакция не найдена', 'danger')
        return redirect(url_for('regular_transactions_list'))
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        amount = request.form.get('amount', type=float)
        category_id = request.form.get('category_id', type=int)
        frequency = request.form.get('frequency', 'monthly')
        comment = request.form.get('comment', '')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        is_active = request.form.get('is_active') == 'on'
        
        # Преобразуем даты
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else regular.start_date
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
        
        success, message = RegularTransactionService.update_regular_transaction(
            regular_id=id,
            name=name,
            amount=amount,
            category_id=category_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            comment=comment,
            is_active=is_active,
            user_id=user_id
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('regular_transactions_list'))
        else:
            flash(message, 'danger')
    
    categories = Category.query.filter_by(user_id=user_id).order_by(Category.type, Category.name).all()
    return render_template('regular_transactions/edit.html', regular=regular, categories=categories)


@app.route('/regular-transactions/<int:id>/delete', methods=['POST'])
@login_required
def regular_transaction_delete(id):
    """Удаление регулярной транзакции"""
    user_id = session['user_id']
    success, message = RegularTransactionService.delete_regular_transaction(id, user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('regular_transactions_list'))


@app.route('/regular-transactions/<int:id>/toggle', methods=['GET'])
@login_required
def regular_transaction_toggle(id):
    """Включить/отключить регулярную транзакцию"""
    user_id = session['user_id']
    success, message = RegularTransactionService.toggle_regular_transaction(id, user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('regular_transactions_list'))


# ----- АВТОМАТИЧЕСКОЕ СОЗДАНИЕ ТРАНЗАКЦИЙ -----

@app.route('/process-regular-transactions', methods=['POST'])
@login_required
def process_regular_transactions():
    """Endpoint для запуска обработки регулярных транзакций"""
    user_id = session['user_id']
    count, messages = RegularTransactionService.process_due_transactions(user_id)
    
    if count > 0:
        flash(f'Создано {count} транзакций', 'success')
        for msg in messages:
            flash(msg, 'info')
    else:
        flash('Нет просроченных регулярных транзакций', 'info')
    
    return redirect(url_for('transactions_list'))

@app.route('/process-all-regular-transactions', methods=['POST'])
@login_required
def process_all_regular_transactions():
    """Создать все пропущенные регулярные транзакции для текущего пользователя"""
    user_id = session['user_id']
    count, messages = RegularTransactionService.process_all_due_transactions(user_id)
    
    if count > 0:
        flash(f'Создано {count} транзакций', 'success')
        for msg in messages[:5]:
            flash(msg, 'info')
    else:
        flash('Нет пропущенных регулярных транзакций', 'info')
    
    return jsonify({'success': True, 'message': f'Создано {count} транзакций', 'count': count})

# ----- API МАРШРУТЫ ДЛЯ ГРАФИКОВ И СТАТИСТИКИ -----

@app.route('/api/stats/last-30-days')
@login_required
def api_last_30_days_stats():
    """API для получения данных за последние 30 дней для графика"""
    user_id = session['user_id']
    data = TransactionService.get_daily_stats_last_30_days(user_id)
    return jsonify(data)


@app.route('/api/stats/period')
@login_required
def api_period_stats():
    """API для получения статистики за произвольный период"""
    user_id = session['user_id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Не указаны даты'}), 400
    
    # Статистика за период
    stats = TransactionService.get_stats_for_period(user_id, start_date, end_date)
    
    # Расходы по категориям
    expenses_by_category = TransactionService.get_expenses_by_category_for_period(
        user_id, start_date, end_date
    )
    
    return jsonify({
        'stats': stats,
        'expenses_by_category': expenses_by_category
    })


@app.route('/categories/<int:id>/limit', methods=['POST'])
@login_required
def category_update_limit(id):
    """Обновление лимита категории"""
    user_id = session['user_id']
    data = request.get_json()
    monthly_limit = data.get('monthly_limit', None)
    
    if monthly_limit is not None:
        monthly_limit = float(monthly_limit)
    
    success, message = CategoryService.update_category_limit(id, monthly_limit, user_id)
    
    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/api/categories-with-budget')
@login_required
def api_categories_with_budget():
    """API для получения категорий с информацией о бюджете"""
    user_id = session['user_id']
    categories = Category.query.filter_by(user_id=user_id, type='expense').all()
    
    result = []
    for cat in categories:
        spent = TransactionService.get_monthly_spending_by_category(user_id, cat.id)
        result.append({
            'id': cat.id,
            'name': cat.name,
            'color': cat.color,
            'monthly_limit': cat.monthly_limit,
            'spent_this_month': spent
        })
    
    return jsonify(result)
    
# Настройка планировщика для автоматического запуска
def setup_scheduler():
    """Настройка планировщика для регулярных транзакций"""
    import threading
    import time
    
    def scheduler_worker():
        with app.app_context():
            while True:
                try:
                    # Проверяем каждые 5 минут
                    time.sleep(300)
                    # Получаем всех пользователей и обрабатываем их транзакции
                    users = User.query.all()
                    for user in users:
                        count, messages = RegularTransactionService.process_due_transactions(user.id)
                        if count > 0:
                            print(f"[Scheduler] Для пользователя {user.username} создано {count} регулярных транзакций")
                except Exception as e:
                    print(f"[Scheduler] Ошибка: {e}")
    
    # Запускаем в отдельном потоке
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()

# ----- АВТОМАТИЧЕСКАЯ ОБРАБОТКА РЕГУЛЯРНЫХ ТРАНЗАКЦИЙ ПРИ ЗАПУСКЕ -----

def process_all_users_regular_transactions():
    """Обработать регулярные транзакции для всех пользователей"""
    with app.app_context():
        users = User.query.all()
        total_count = 0
        for user in users:
            count, messages = RegularTransactionService.process_all_due_transactions(user.id)
            total_count += count
            if count > 0:
                print(f"[Авто] Для пользователя {user.username} создано {count} регулярных транзакций")
        return total_count


# ----- ПЛАНИРОВЩИК ДЛЯ АВТОМАТИЧЕСКОГО ЗАПУСКА РАЗ В СУТКИ -----

def setup_scheduler():
    """Настройка планировщика для регулярных транзакций"""
    import threading
    import time
    
    def scheduler_worker():
        with app.app_context():
            while True:
                try:
                    # Проверяем каждые 24 часа (86400 секунд)
                    time.sleep(86400)
                    
                    # Создаём все пропущенные транзакции для всех пользователей
                    users = User.query.all()
                    for user in users:
                        count, messages = RegularTransactionService.process_all_due_transactions(user.id)
                        if count > 0:
                            print(f"[Планировщик] Для пользователя {user.username} создано {count} регулярных транзакций")
                            
                except Exception as e:
                    print(f"[Планировщик] Ошибка: {e}")
    
    scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
    scheduler_thread.start()


# ----- ЗАПУСК АВТОМАТИЧЕСКОЙ ОБРАБОТКИ ПРИ СТАРТЕ -----
def run_initial_processing():
    """Запускается один раз при старте приложения"""
    import threading
    import time
    
    def delayed_processing():
        # Ждём 5 секунд после запуска, чтобы БД точно инициализировалась
        time.sleep(5)
        count = process_all_users_regular_transactions()
        print(f"[Старт] Создано {count} регулярных транзакций при запуске")
    
    thread = threading.Thread(target=delayed_processing, daemon=True)
    thread.start()

# ----- МАРШРУТЫ СЧЕТОВ -----

@app.route('/accounts')
@login_required
def accounts_list():
    """Список всех счетов"""
    user_id = session['user_id']
    accounts = AccountService.get_all_accounts(user_id)
    
    # Получаем балансы
    accounts_with_balance = []
    for acc in accounts:
        accounts_with_balance.append({
            'id': acc.id,
            'name': acc.name,
            'type': acc.type,
            'icon': acc.icon,
            'color': acc.color,
            'balance': acc.current_balance,
            'initial_balance': acc.initial_balance
        })
    
    return render_template('accounts/list.html', accounts=accounts_with_balance)


@app.route('/accounts/create', methods=['GET', 'POST'])
@login_required
def account_create():
    """Создание нового счета"""
    user_id = session['user_id']
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        type = request.form.get('type', 'cash')
        initial_balance = request.form.get('initial_balance', 0, type=float)
        icon = request.form.get('icon', 'fa-wallet')
        color = request.form.get('color', '#007bff')
        
        success, message, account = AccountService.create_account(
            name=name,
            type=type,
            user_id=user_id,
            initial_balance=initial_balance,
            icon=icon,
            color=color
        )
        
        if success:
            flash(message, 'success')
            return redirect(url_for('accounts_list'))
        else:
            flash(message, 'danger')
    
    return render_template('accounts/create.html')


@app.route('/accounts/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def account_edit(id):
    """Редактирование счета"""
    user_id = session['user_id']
    account = AccountService.get_account_by_id(id, user_id)
    
    if not account:
        flash('Счет не найден', 'danger')
        return redirect(url_for('accounts_list'))
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        initial_balance = request.form.get('initial_balance', 0, type=float)
        
        success, message = AccountService.update_account(id, name, initial_balance, user_id)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('accounts_list'))
        else:
            flash(message, 'danger')
    
    return render_template('accounts/edit.html', account=account)


@app.route('/accounts/<int:id>/delete', methods=['POST'])
@login_required
def account_delete(id):
    """Удаление счета"""
    user_id = session['user_id']
    success, message = AccountService.delete_account(id, user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('accounts_list'))


@app.route('/api/accounts/balance')
@login_required
def api_accounts_balance():
    """API для получения балансов всех счетов"""
    user_id = session['user_id']
    accounts = AccountService.get_all_accounts(user_id)
    
    result = []
    for acc in accounts:
        result.append({
            'id': acc.id,
            'name': acc.name,
            'type': acc.type,
            'icon': acc.icon,
            'color': acc.color,
            'balance': acc.current_balance
        })
    
    return jsonify(result)    
# ----- РЕЗЕРВНОЕ КОПИРОВАНИЕ -----

@app.route('/backup/download')
@login_required
def backup_download():
    """Скачать резервную копию базы данных"""
    import os
    from flask import send_file
    from datetime import datetime
    
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'finance.db')
    
    if not os.path.exists(db_path):
        flash('Файл базы данных не найден', 'danger')
        return redirect(url_for('index'))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'finance_backup_{timestamp}.db'
    
    return send_file(
        db_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/x-sqlite3'
    )


@app.route('/backup/restore', methods=['POST'])
@login_required
def backup_restore():
    """Восстановить базу данных из файла"""
    import os
    import shutil
    
    if 'backup_file' not in request.files:
        flash('Файл не выбран', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['backup_file']
    
    if file.filename == '':
        flash('Файл не выбран', 'danger')
        return redirect(url_for('index'))
    
    if not file.filename.endswith('.db'):
        flash('Неверный формат файла. Ожидается .db файл', 'danger')
        return redirect(url_for('index'))
    
    # Создаем резервную копию текущей БД перед восстановлением
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'finance.db')
    backup_path = os.path.join(os.path.dirname(__file__), 'instance', 'finance_backup_before_restore.db')
    
    if os.path.exists(db_path):
        shutil.copy2(db_path, backup_path)
        flash('Создана резервная копия текущей базы данных', 'info')
    
    # Сохраняем загруженный файл
    file.save(db_path)
    
    flash('База данных успешно восстановлена! Перезагрузите страницу.', 'success')
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    # Запускаем автоматическую обработку при старте
    run_initial_processing()
    
    # Запускаем планировщик для ежедневной проверки
    setup_scheduler()
    
    app.run(debug=True, port=5000)