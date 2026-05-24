from models import db, Category, Transaction, RegularTransaction
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import and_


class RegularTransactionService:
    """Сервис для работы с регулярными транзакциями"""

    @staticmethod
    def get_all_regular_transactions(user_id: int) -> List[RegularTransaction]:
        """Получить все регулярные транзакции пользователя"""
        return RegularTransaction.query.filter_by(user_id=user_id).order_by(RegularTransaction.next_execution).all()

    @staticmethod
    def get_active_regular_transactions(user_id: int) -> List[RegularTransaction]:
        """Получить активные регулярные транзакции пользователя"""
        return RegularTransaction.query.filter_by(user_id=user_id, is_active=True).all()

    @staticmethod
    def get_regular_transaction_by_id(regular_id: int, user_id: int) -> Optional[RegularTransaction]:
        """Получить регулярную транзакцию по ID (с проверкой принадлежности пользователю)"""
        return RegularTransaction.query.filter_by(id=regular_id, user_id=user_id).first()

    @staticmethod
    def create_regular_transaction(
        name: str,
        amount: float,
        category_id: int,
        frequency: str,
        start_date: datetime,
        end_date: Optional[datetime],
        comment: str,
        type: str,
        user_id: int
    ) -> Tuple[bool, str, Optional[RegularTransaction]]:
        """Создать новую регулярную транзакцию"""
        
        if not name or not name.strip():
            return False, "Название не может быть пустым", None
        
        if amount <= 0:
            return False, "Сумма должна быть положительной", None
        
        if frequency not in ['daily', 'weekly', 'monthly']:
            return False, "Неверная периодичность", None
        
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена", None
        
        if category.type != type:
            return False, f"Выбранная категория не подходит для типа '{type}'", None
        
        next_execution = start_date
        
        regular = RegularTransaction(
            name=name.strip(),
            amount=amount,
            comment=comment.strip() if comment else '',
            category_id=category_id,
            type=type,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_execution=next_execution,
            is_active=True,
            user_id=user_id
        )
        
        try:
            db.session.add(regular)
            db.session.commit()
            return True, "Регулярная транзакция успешно создана", regular
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при создании: {str(e)}", None

    @staticmethod
    def update_regular_transaction(
        regular_id: int,
        name: str,
        amount: float,
        category_id: int,
        frequency: str,
        start_date: datetime,
        end_date: Optional[datetime],
        comment: str,
        is_active: bool,
        user_id: int
    ) -> Tuple[bool, str]:
        """Обновить регулярную транзакцию"""
        
        regular = RegularTransaction.query.filter_by(id=regular_id, user_id=user_id).first()
        if not regular:
            return False, "Регулярная транзакция не найдена"
        
        if not name or not name.strip():
            return False, "Название не может быть пустым"
        
        if amount <= 0:
            return False, "Сумма должна быть положительной"
        
        if frequency not in ['daily', 'weekly', 'monthly']:
            return False, "Неверная периодичность"
        
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена"
        
        if category.type != regular.type:
            return False, f"Выбранная категория не подходит для типа '{regular.type}'"
        
        regular.name = name.strip()
        regular.amount = amount
        regular.comment = comment.strip() if comment else ''
        regular.category_id = category_id
        regular.frequency = frequency
        regular.start_date = start_date
        regular.end_date = end_date
        regular.is_active = is_active
        
        regular.next_execution = RegularTransactionService._calculate_next_execution(
            regular.last_executed or start_date,
            frequency
        )
        
        try:
            db.session.commit()
            return True, "Регулярная транзакция успешно обновлена"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при обновлении: {str(e)}"

    @staticmethod
    def delete_regular_transaction(regular_id: int, user_id: int) -> Tuple[bool, str]:
        """Удалить регулярную транзакцию"""
        
        regular = RegularTransaction.query.filter_by(id=regular_id, user_id=user_id).first()
        if not regular:
            return False, "Регулярная транзакция не найдена"
        
        try:
            db.session.delete(regular)
            db.session.commit()
            return True, "Регулярная транзакция успешно удалена"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при удалении: {str(e)}"

    @staticmethod
    def toggle_regular_transaction(regular_id: int, user_id: int) -> Tuple[bool, str]:
        """Включить/отключить регулярную транзакцию"""
        
        regular = RegularTransaction.query.filter_by(id=regular_id, user_id=user_id).first()
        if not regular:
            return False, "Регулярная транзакция не найдена"
        
        regular.is_active = not regular.is_active
        
        try:
            db.session.commit()
            status = "активирована" if regular.is_active else "деактивирована"
            return True, f"Регулярная транзакция {status}"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при изменении статуса: {str(e)}"

    @staticmethod
    def _calculate_next_execution(last_date: datetime, frequency: str) -> datetime:
        """Вычислить следующую дату выполнения"""
        if frequency == 'daily':
            return last_date + timedelta(days=1)
        elif frequency == 'weekly':
            return last_date + timedelta(weeks=1)
        elif frequency == 'monthly':
            if last_date.month == 12:
                return last_date.replace(year=last_date.year + 1, month=1)
            else:
                return last_date.replace(month=last_date.month + 1)
        return last_date

    @staticmethod
    def process_due_transactions(user_id: int) -> Tuple[int, List[str]]:
        """
        Обработать просроченные регулярные транзакции пользователя (только одну пропущенную)
        """
        now = datetime.now()
        due_transactions = RegularTransaction.query.filter(
            and_(
                RegularTransaction.user_id == user_id,
                RegularTransaction.is_active == True,
                RegularTransaction.next_execution <= now,
                db.or_(
                    RegularTransaction.end_date == None,
                    RegularTransaction.end_date >= now
                )
            )
        ).all()
        
        created_count = 0
        messages = []
        
        for regular in due_transactions:
            try:
                transaction = Transaction(
                    amount=regular.amount,
                    date=now,
                    comment=f"[Регулярная] {regular.comment}" if regular.comment else "Регулярная транзакция",
                    type=regular.type,
                    category_id=regular.category_id,
                    regular_transaction_id=regular.id,
                    is_regular=True,
                    user_id=user_id
                )
                
                db.session.add(transaction)
                
                regular.last_executed = now
                regular.next_execution = RegularTransactionService._calculate_next_execution(
                    regular.next_execution,
                    regular.frequency
                )
                
                db.session.commit()
                created_count += 1
                messages.append(f"Создана транзакция: {regular.name} - {regular.amount} ₽")
                
            except Exception as e:
                db.session.rollback()
                messages.append(f"Ошибка при создании {regular.name}: {str(e)}")
        
        return created_count, messages

    @staticmethod
    def process_all_due_transactions(user_id: int) -> Tuple[int, List[str]]:
        """
        Создать ВСЕ пропущенные регулярные транзакции за всё время
        (для каждого месяца/недели/дня с даты начала до текущей даты)
        """
        regulars = RegularTransaction.query.filter_by(user_id=user_id, is_active=True).all()
        
        now = datetime.now()
        created_count = 0
        messages = []
        
        for regular in regulars:
            start_date = regular.last_executed or regular.start_date
            
            if start_date > now:
                continue
            
            current_date = start_date
            dates_to_create = []
            
            # Если last_executed уже есть, начинаем со следующей даты
            if regular.last_executed:
                current_date = RegularTransactionService._calculate_next_execution(
                    regular.last_executed,
                    regular.frequency
                )
            
            # Генерируем все даты до сегодня
            while current_date <= now:
                if regular.end_date and current_date > regular.end_date:
                    break
                
                dates_to_create.append(current_date)
                
                if regular.frequency == 'daily':
                    current_date += timedelta(days=1)
                elif regular.frequency == 'weekly':
                    current_date += timedelta(weeks=1)
                elif regular.frequency == 'monthly':
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
            
            # Создаём транзакции для всех дат
            for create_date in dates_to_create:
                try:
                    transaction = Transaction(
                        amount=regular.amount,
                        date=create_date,
                        comment=f"[Регулярная] {regular.comment}" if regular.comment else "Регулярная транзакция",
                        type=regular.type,
                        category_id=regular.category_id,
                        regular_transaction_id=regular.id,
                        is_regular=True,
                        user_id=user_id
                    )
                    db.session.add(transaction)
                    created_count += 1
                    messages.append(f"Создана транзакция: {regular.name} - {regular.amount} ₽ за {create_date.strftime('%d.%m.%Y')}")
                    
                except Exception as e:
                    db.session.rollback()
                    messages.append(f"Ошибка при создании {regular.name}: {str(e)}")
            
            # Обновляем last_executed и next_execution
            if dates_to_create:
                regular.last_executed = dates_to_create[-1]
                regular.next_execution = RegularTransactionService._calculate_next_execution(
                    regular.last_executed,
                    regular.frequency
                )
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            messages.append(f"Ошибка при сохранении: {str(e)}")
        
        return created_count, messages