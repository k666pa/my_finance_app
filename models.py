from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Связи
    categories = db.relationship('Category', backref='user', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    regular_transactions = db.relationship('RegularTransaction', backref='user', lazy=True)
    accounts = db.relationship('Account', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    color = db.Column(db.String(7), default='#808080')
    order = db.Column(db.Integer, default=0)
    monthly_limit = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Внешний ключ на пользователя
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    transactions = db.relationship('Transaction', backref='category', lazy=True, cascade='all, delete-orphan')
    regular_transactions = db.relationship('RegularTransaction', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # cash, card, savings
    icon = db.Column(db.String(50), default='fa-wallet')
    color = db.Column(db.String(7), default='#007bff')
    initial_balance = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Внешний ключ на пользователя
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Связь с транзакциями
    transactions = db.relationship('Transaction', backref='account', lazy=True)

    def __repr__(self):
        return f'<Account {self.name}>'

    @property
    def current_balance(self):
        """Расчет текущего баланса счета"""
        from sqlalchemy import func
        income = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.account_id == self.id, Transaction.type == 'income').scalar() or 0
        expense = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.account_id == self.id, Transaction.type == 'expense').scalar() or 0
        return self.initial_balance + income - expense

    @property
    def formatted_balance(self):
        return f"{self.current_balance:,.2f}".replace(',', ' ')


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    comment = db.Column(db.String(200), nullable=True)
    type = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    regular_transaction_id = db.Column(db.Integer, db.ForeignKey('regular_transactions.id'), nullable=True)
    is_regular = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Transaction {self.type} {self.amount}>'

    @property
    def formatted_date(self):
        return self.date.strftime('%d.%m.%Y')

    @property
    def formatted_amount(self):
        return f"{self.amount:,.2f}".replace(',', ' ')


class RegularTransaction(db.Model):
    __tablename__ = 'regular_transactions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    comment = db.Column(db.String(200), nullable=True)
    type = db.Column(db.String(10), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)

    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    end_date = db.Column(db.DateTime, nullable=True)
    last_executed = db.Column(db.DateTime, nullable=True)
    next_execution = db.Column(db.DateTime, nullable=False)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    transactions = db.relationship('Transaction', backref='regular_transaction', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<RegularTransaction {self.name}>'

    @property
    def frequency_display(self):
        frequencies = {'daily': 'Ежедневно', 'weekly': 'Еженедельно', 'monthly': 'Ежемесячно'}
        return frequencies.get(self.frequency, self.frequency)

    @property
    def formatted_amount(self):
        return f"{self.amount:,.2f}".replace(',', ' ')

    @property
    def formatted_start_date(self):
        return self.start_date.strftime('%d.%m.%Y') if self.start_date else '-'

    @property
    def formatted_end_date(self):
        return self.end_date.strftime('%d.%m.%Y') if self.end_date else 'Бессрочно'

    @property
    def formatted_last_executed(self):
        return self.last_executed.strftime('%d.%m.%Y') if self.last_executed else 'Никогда'

    @property
    def formatted_next_execution(self):
        return self.next_execution.strftime('%d.%m.%Y')