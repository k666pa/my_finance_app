from models import db, Account
from typing import List, Optional, Tuple


class AccountService:
    """Сервис для работы со счетами"""

    @staticmethod
    def get_all_accounts(user_id: int) -> List[Account]:
        """Получить все счета пользователя"""
        return Account.query.filter_by(user_id=user_id, is_active=True).order_by(Account.order).all()

    @staticmethod
    def get_account_by_id(account_id: int, user_id: int) -> Optional[Account]:
        """Получить счет по ID"""
        return Account.query.filter_by(id=account_id, user_id=user_id).first()

    @staticmethod
    def create_account(name: str, type: str, user_id: int, initial_balance: float = 0, 
                       icon: str = 'fa-wallet', color: str = '#007bff') -> Tuple[bool, str, Optional[Account]]:
        """Создать новый счет"""
        if not name or not name.strip():
            return False, "Название счета не может быть пустым", None

        if type not in ['cash', 'card', 'savings']:
            return False, "Неверный тип счета", None

        max_order = db.session.query(db.func.max(Account.order)).filter_by(user_id=user_id).scalar() or 0

        account = Account(
            name=name.strip(),
            type=type,
            user_id=user_id,
            initial_balance=initial_balance,
            icon=icon,
            color=color,
            order=max_order + 1
        )

        try:
            db.session.add(account)
            db.session.commit()
            return True, f"Счет '{name}' успешно создан", account
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при создании счета: {str(e)}", None

    @staticmethod
    def update_account(account_id: int, name: str, initial_balance: float, user_id: int) -> Tuple[bool, str]:
        """Обновить счет"""
        account = Account.query.filter_by(id=account_id, user_id=user_id).first()
        if not account:
            return False, "Счет не найден"

        account.name = name.strip()
        account.initial_balance = initial_balance

        try:
            db.session.commit()
            return True, "Счет успешно обновлен"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при обновлении: {str(e)}"

    @staticmethod
    def delete_account(account_id: int, user_id: int) -> Tuple[bool, str]:
        """Удалить счет (только если нет транзакций)"""
        account = Account.query.filter_by(id=account_id, user_id=user_id).first()
        if not account:
            return False, "Счет не найден"

        if account.transactions:
            return False, "Нельзя удалить счет, на котором есть транзакции"

        try:
            db.session.delete(account)
            db.session.commit()
            return True, "Счет успешно удален"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при удалении: {str(e)}"