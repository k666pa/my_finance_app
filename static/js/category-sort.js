/**
 * Управление сортировкой категорий
 */
class CategorySorter {
    constructor() {
        this.init();
        this.initSorting();
    }

    init() {
        // Находим все контейнеры с категориями
        this.expensesContainer = document.querySelector('#expensesColumn .list-group');
        this.incomesContainer = document.querySelector('#incomesColumn .list-group');
        
        if (!this.expensesContainer && !this.incomesContainer) return;
    }

    initSorting() {
        // Инициализируем сортировку для каждой колонки
        if (this.expensesContainer) {
            this.initColumnSorting(this.expensesContainer, 'expense');
        }
        if (this.incomesContainer) {
            this.initColumnSorting(this.incomesContainer, 'income');
        }
    }

    initColumnSorting(container, type) {
        const items = container.querySelectorAll('.category-item');
        if (items.length === 0) return;

        items.forEach((item, index) => {
            const categoryId = item.dataset.categoryId;
            const upBtn = item.querySelector('.sort-up');
            const downBtn = item.querySelector('.sort-down');

            // Обновляем состояние кнопок
            this.updateButtonState(upBtn, downBtn, index, items.length);

            // Добавляем обработчики
            if (upBtn) {
                upBtn.onclick = (e) => this.moveCategory(e, categoryId, 'up', type, item);
            }
            if (downBtn) {
                downBtn.onclick = (e) => this.moveCategory(e, categoryId, 'down', type, item);
            }
        });
    }

    updateButtonState(upBtn, downBtn, index, total) {
        if (upBtn) {
            if (index === 0) {
                upBtn.classList.add('disabled');
                upBtn.disabled = true;
            } else {
                upBtn.classList.remove('disabled');
                upBtn.disabled = false;
            }
        }

        if (downBtn) {
            if (index === total - 1) {
                downBtn.classList.add('disabled');
                downBtn.disabled = true;
            } else {
                downBtn.classList.remove('disabled');
                downBtn.disabled = false;
            }
        }
    }

    async moveCategory(event, categoryId, direction, type, item) {
        event.preventDefault();
        event.stopPropagation();

        const button = event.currentTarget;
        if (button.disabled) return;

        // Показываем загрузку
        const originalHtml = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';
        
        // Добавляем класс анимации к элементу
        item.classList.add('moving');

        try {
            const response = await fetch(`/categories/${categoryId}/move`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ direction: direction })
            });

            const data = await response.json();

            if (data.success) {
                // Перезагружаем страницу для простоты
                // В реальном проекте можно обновить UI без перезагрузки
                setTimeout(() => {
                    location.reload();
                }, 300);
            } else {
                alert('Ошибка при перемещении: ' + data.message);
                button.disabled = false;
                button.innerHTML = originalHtml;
                item.classList.remove('moving');
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Произошла ошибка при перемещении');
            button.disabled = false;
            button.innerHTML = originalHtml;
            item.classList.remove('moving');
        }
    }
}

// Инициализация после загрузки страницы и после каждого обновления
function initCategorySorter() {
    new CategorySorter();
}

// Запускаем при загрузке
document.addEventListener('DOMContentLoaded', initCategorySorter);

// Также запускаем после AJAX обновлений (если они будут)
document.addEventListener('categories-updated', initCategorySorter);