from models import db, Category
from typing import List, Optional, Tuple


class CategoryService:
    """Сервис для работы с категориями"""

    @staticmethod
    def get_all_categories(user_id: int) -> List[Category]:
        """Получить все категории пользователя, отсортированные по порядку"""
        return Category.query.filter_by(user_id=user_id).order_by(Category.type, Category.order).all()

    @staticmethod
    def get_categories_by_type(user_id: int, type: str) -> List[Category]:
        """Получить категории определённого типа ('income' или 'expense')"""
        return Category.query.filter_by(user_id=user_id, type=type).order_by(Category.order).all()

    @staticmethod
    def get_category_by_id(category_id: int, user_id: int) -> Optional[Category]:
        """Получить категорию по ID (с проверкой принадлежности пользователю)"""
        return Category.query.filter_by(id=category_id, user_id=user_id).first()

    @staticmethod
    def create_category(name: str, type: str, color: str, user_id: int, monthly_limit: float = None) -> Tuple[bool, str, Optional[Category]]:
        """
        Создать новую категорию
        Возвращает: (успех, сообщение, созданная категория)
        """
        # Валидация
        if not name or not name.strip():
            return False, "Название категории не может быть пустым", None

        if type not in ['income', 'expense']:
            return False, "Тип категории должен быть 'income' или 'expense'", None

        # Проверка на дубликат среди категорий пользователя
        existing = Category.query.filter_by(user_id=user_id, name=name.strip()).first()
        if existing:
            return False, f"Категория с названием '{name}' уже существует", None

        # Определяем максимальный порядок для нового типа категории
        max_order = db.session.query(db.func.max(Category.order)).filter_by(user_id=user_id, type=type).scalar() or 0

        # Создаём объект
        category = Category(
            name=name.strip(),
            type=type,
            color=color,
            order=max_order + 1,
            monthly_limit=monthly_limit,
            user_id=user_id
        )

        # Сохраняем в БД
        try:
            db.session.add(category)
            db.session.commit()
            return True, "Категория успешно создана", category
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при создании категории: {str(e)}", None

    @staticmethod
    def update_category(category_id: int, name: str, type: str, color: str, user_id: int, monthly_limit: float = None) -> Tuple[bool, str]:
        """Обновить существующую категорию"""
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена"

        # Валидация
        if not name or not name.strip():
            return False, "Название категории не может быть пустым"

        if type not in ['income', 'expense']:
            return False, "Тип категории должен быть 'income' или 'expense'"

        # Проверка на дубликат (если имя меняется)
        if name.strip() != category.name:
            existing = Category.query.filter_by(user_id=user_id, name=name.strip()).first()
            if existing:
                return False, f"Категория с названием '{name}' уже существует"

        # Обновляем поля
        category.name = name.strip()
        category.type = type
        category.color = color
        category.monthly_limit = monthly_limit

        try:
            db.session.commit()
            return True, "Категория успешно обновлена"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при обновлении: {str(e)}"

    @staticmethod
    def delete_category(category_id: int, user_id: int) -> Tuple[bool, str]:
        """Удалить категорию (только если нет связанных транзакций)"""
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена"

        # Проверка на наличие связанных транзакций
        if category.transactions:
            return False, "Нельзя удалить категорию, у которой есть связанные транзакции"

        try:
            db.session.delete(category)
            db.session.commit()
            return True, "Категория успешно удалена"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при удалении: {str(e)}"

    @staticmethod
    def move_category(category_id: int, direction: str, user_id: int) -> Tuple[bool, str]:
        """
        Переместить категорию вверх или вниз
        direction: 'up' или 'down'
        """
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена"
        
        # Определяем соседнюю категорию для обмена
        if direction == 'up':
            neighbor = Category.query.filter(
                Category.user_id == user_id,
                Category.type == category.type,
                Category.order < category.order
            ).order_by(Category.order.desc()).first()
        else:  # down
            neighbor = Category.query.filter(
                Category.user_id == user_id,
                Category.type == category.type,
                Category.order > category.order
            ).order_by(Category.order.asc()).first()
        
        if not neighbor:
            return False, f"Нельзя переместить {('вверх' if direction == 'up' else 'вниз')}"
        
        # Меняем order местами
        category.order, neighbor.order = neighbor.order, category.order
        
        try:
            db.session.commit()
            return True, f"Категория перемещена {('вверх' if direction == 'up' else 'вниз')}"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при перемещении: {str(e)}"

    @staticmethod
    def update_category_limit(category_id: int, monthly_limit: float, user_id: int) -> Tuple[bool, str]:
        """Обновить месячный лимит категории"""
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return False, "Категория не найдена"
        
        category.monthly_limit = monthly_limit if monthly_limit > 0 else None
        
        try:
            db.session.commit()
            if monthly_limit > 0:
                return True, f"Лимит для категории '{category.name}' установлен: {monthly_limit:.2f} ₽"
            else:
                return True, f"Лимит для категории '{category.name}' удалён"
        except Exception as e:
            db.session.rollback()
            return False, f"Ошибка при обновлении лимита: {str(e)}"