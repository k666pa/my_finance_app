from models import db, Transaction, Category
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import desc, func


class TransactionService:
    """Сервис для работы с транзакциями"""

    @staticmethod
    def get_all_transactions(user_id: int) -> List[Transaction]:
        """Получить все транзакции пользователя, отсортированные по дате (свежие сверху)"""
        return Transaction.query.filter_by(user_id=user_id).order_by(desc(Transaction.date)).all()

    @staticmethod
    def get_transaction_by_id(transaction_id: int, user_id: int) -> Optional[Transaction]:
        """Получить транзакцию по ID (с проверкой принадлежности пользователю)"""
        return Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()

    @staticmethod
    def get_transactions_filtered(
        user_id: int,
        period: str = 'all',
        category_id: Optional[int] = None,
        type: Optional[str] = None
    ) -> List[Transaction]:
        """
        Получить транзакции с фильтрацией
        period: 'today', 'week', 'month', 'all'
        """
        query = Transaction.query.filter_by(user_id=user_id)

        # Фильтр по периоду
        if period != 'all':
            today = datetime.now().date()
            
            if period == 'today':
                start_date = datetime.combine(today, datetime.min.time())
                query = query.filter(Transaction.date >= start_date)
            
            elif period == 'week':
                start_date = datetime.combine(today - timedelta(days=7), datetime.min.time())
                query = query.filter(Transaction.date >= start_date)
            
            elif period == 'month':
                start_date = datetime.combine(today - timedelta(days=30), datetime.min.time())
                query = query.filter(Transaction.date >= start_date)

        # Фильтр по категории
        if category_id:
            query = query.filter(Transaction.category_id == category_id)

        # Фильтр по типу
        if type:
            query = query.filter(Transaction.type == type)

        return query.order_by(desc(Transaction.date)).all()

    @staticmethod
    def create_transaction(
        amount: float,
        date: datetime,
        category_id: int,
        account_id: int,
        comment: str,
        type: str,
        user_id: int
    ) -> Tuple[bool, str, Optional[Transaction]]:
        """Создать новую транзакцию"""
        
        if amount <= 0:
            return False, "Сумма должна быть положительной", None

        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена", None

        from models import Account
        account = Account.query.filter_by(id=account_id, user_id=user_id).first()
        if not account:
            return False, "Счет не найден", None

        if category.type != type:
            return False, f"Выбранная категория не подходит для типа '{type}'", None

        transaction = Transaction(
            amount=amount,
            date=date,
            comment=comment.strip() if comment else '',
            category_id=category_id,
            account_id=account_id,
            type=type,
            user_id=user_id
        )

        try:
            db.session.add(transaction)
            db.session.commit()
            return True, "Транзакция успешно создана", transaction
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при создании транзакции: {str(e)}", None

    @staticmethod
    def update_transaction(
        transaction_id: int,
        amount: float,
        date: datetime,
        category_id: int,
        account_id: int,
        comment: str,
        user_id: int
    ) -> Tuple[bool, str]:
        """Обновить существующую транзакцию"""
        
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        if not transaction:
            return False, "Транзакция не найдена"

        if amount <= 0:
            return False, "Сумма должна быть положительной"

        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена"

        from models import Account
        account = Account.query.filter_by(id=account_id, user_id=user_id).first()
        if not account:
            return False, "Счет не найден"

        if category.type != transaction.type:
            return False, f"Выбранная категория не подходит для типа '{transaction.type}'"

        transaction.amount = amount
        transaction.date = date
        transaction.comment = comment.strip() if comment else ''
        transaction.category_id = category_id
        transaction.account_id = account_id

        try:
            db.session.commit()
            return True, "Транзакция успешно обновлена"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при обновлении: {str(e)}"

    @staticmethod
    def delete_transaction(transaction_id: int, user_id: int) -> Tuple[bool, str]:
        """Удалить транзакцию"""
        
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=user_id).first()
        if not transaction:
            return False, "Транзакция не найдена"

        try:
            db.session.delete(transaction)
            db.session.commit()
            return True, "Транзакция успешно удалена"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при удалении: {str(e)}"

    @staticmethod
    def get_stats(user_id: int) -> dict:
        """Получить статистику по транзакциям пользователя"""
        
        # Общая сумма доходов
        total_income = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, Transaction.type == 'income').scalar() or 0
        
        # Общая сумма расходов
        total_expense = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, Transaction.type == 'expense').scalar() or 0
        
        # Баланс
        balance = total_income - total_expense
        
        # Количество транзакций
        transactions_count = Transaction.query.filter_by(user_id=user_id).count()
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': balance,
            'transactions_count': transactions_count
        }

    @staticmethod
    def get_daily_stats_last_30_days(user_id: int) -> dict:
        """Получить ежедневную статистику доходов/расходов за последние 30 дней"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=29)
        
        # Создаем словарь для всех дней
        date_range = {}
        current = start_date
        while current <= end_date:
            date_range[current] = {'income': 0, 'expense': 0}
            current += timedelta(days=1)
        
        # Получаем транзакции за период
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.date >= datetime.combine(start_date, datetime.min.time()),
            Transaction.date <= datetime.combine(end_date, datetime.max.time())
        ).all()
        
        for t in transactions:
            date_key = t.date.date()
            if date_key in date_range:
                if t.type == 'income':
                    date_range[date_key]['income'] += t.amount
                else:
                    date_range[date_key]['expense'] += t.amount
        
        # Формируем результат
        result = {
            'dates': [d.strftime('%d.%m') for d in date_range.keys()],
            'income': [date_range[d]['income'] for d in date_range.keys()],
            'expense': [date_range[d]['expense'] for d in date_range.keys()],
            'balance': [date_range[d]['income'] - date_range[d]['expense'] for d in date_range.keys()]
        }
        return result

    @staticmethod
    def get_stats_for_period(user_id: int, start_date: str, end_date: str) -> dict:
        """Получить статистику за произвольный период"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        end = end.replace(hour=23, minute=59, second=59)
        
        # Доходы
        total_income = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id, 
                    Transaction.type == 'income',
                    Transaction.date >= start,
                    Transaction.date <= end).scalar() or 0
        
        # Расходы
        total_expense = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id,
                    Transaction.type == 'expense',
                    Transaction.date >= start,
                    Transaction.date <= end).scalar() or 0
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': total_income - total_expense,
            'start_date': start.strftime('%d.%m.%Y'),
            'end_date': end.strftime('%d.%m.%Y')
        }

    @staticmethod
    def get_expenses_by_category_for_period(user_id: int, start_date: str, end_date: str) -> list:
        """Получить расходы по категориям за период"""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        end = end.replace(hour=23, minute=59, second=59)
        
        results = db.session.query(
            Category.name,
            Category.color,
            func.sum(Transaction.amount).label('total')
        ).join(Transaction, Transaction.category_id == Category.id)\
         .filter(Transaction.user_id == user_id,
                 Transaction.type == 'expense',
                 Transaction.date >= start,
                 Transaction.date <= end)\
         .group_by(Category.id, Category.name, Category.color)\
         .order_by(func.sum(Transaction.amount).desc()).all()
        
        total_expense = sum(r.total for r in results) if results else 0
        
        expenses = []
        for r in results:
            expenses.append({
                'name': r.name,
                'color': r.color,
                'amount': float(r.total),
                'percentage': (float(r.total) / total_expense * 100) if total_expense > 0 else 0
            })
        
        return expenses

    @staticmethod
    def get_monthly_spending_by_category(user_id: int, category_id: int) -> float:
        """Получить сумму расходов за текущий месяц по конкретной категории"""
        now = datetime.now()
        start_of_month = datetime(now.year, now.month, 1)
        
        total = db.session.query(func.sum(Transaction.amount))\
            .filter(Transaction.user_id == user_id,
                    Transaction.category_id == category_id,
                    Transaction.type == 'expense',
                    Transaction.date >= start_of_month).scalar() or 0
        
        return total