/**
 * Управление фильтрацией транзакций
 */
class TransactionFilters {
    constructor() {
        this.init();
    }

    init() {
        this.periodFilter = document.getElementById('periodFilter');
        this.categoryFilter = document.getElementById('categoryFilter');
        this.typeFilter = document.getElementById('typeFilter');
        this.applyBtn = document.getElementById('applyFilters');
        this.resetBtn = document.getElementById('resetFilters');
        this.table = document.getElementById('transactionsTable');
        
        if (!this.table) return;
        
        this.bindEvents();
        this.loadFiltersFromURL();
    }

    bindEvents() {
        if (this.applyBtn) {
            this.applyBtn.addEventListener('click', () => this.applyFilters());
        }
        
        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', () => this.resetFilters());
        }
        
        // Автоматическое применение при изменении (опционально)
        // [this.periodFilter, this.categoryFilter, this.typeFilter].forEach(filter => {
        //     if (filter) filter.addEventListener('change', () => this.applyFilters());
        // });
    }

    loadFiltersFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        
        if (urlParams.has('period')) {
            this.periodFilter.value = urlParams.get('period');
        }
        
        if (urlParams.has('category')) {
            this.categoryFilter.value = urlParams.get('category');
        }
        
        if (urlParams.has('type')) {
            this.typeFilter.value = urlParams.get('type');
        }
    }

    applyFilters() {
        const params = new URLSearchParams();
        
        if (this.periodFilter && this.periodFilter.value !== 'all') {
            params.set('period', this.periodFilter.value);
        }
        
        if (this.categoryFilter && this.categoryFilter.value !== 'all') {
            params.set('category', this.categoryFilter.value);
        }
        
        if (this.typeFilter && this.typeFilter.value !== 'all') {
            params.set('type', this.typeFilter.value);
        }
        
        // Добавляем индикатор загрузки
        this.showLoading();
        
        // Перенаправляем с параметрами
        window.location.href = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    }

    resetFilters() {
        // Сбрасываем все фильтры на значения по умолчанию
        if (this.periodFilter) this.periodFilter.value = 'all';
        if (this.categoryFilter) this.categoryFilter.value = 'all';
        if (this.typeFilter) this.typeFilter.value = 'all';
        
        // Применяем сброс
        this.applyFilters();
    }

    showLoading() {
        // Показываем индикатор загрузки
        if (this.table) {
            this.table.style.opacity = '0.5';
            this.table.classList.add('loading');
        }
    }
}

// Инициализация после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    new TransactionFilters();
});