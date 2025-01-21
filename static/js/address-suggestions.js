import ymaps from 'ymaps';

// Инициализация подсказок адресов
window.addEventListener('load', function() {
    console.log('Страница загружена, инициализируем API...');
    
    // Загружаем API с нашим ключом
    ymaps.load('https://api-maps.yandex.ru/2.1/?apikey=d331e1e4-df6a-4cfa-a00b-6e5330724c15&lang=ru_RU')
        .then(maps => {
            console.log('API Яндекс.Карт загружен успешно');
            
            // Получаем поле ввода адреса
            const addressInput = document.getElementById('delivery_address');
            if (!addressInput) {
                console.error('Поле ввода не найдено!');
                return;
            }

            try {
                // Создаем экземпляр подсказок
                const suggestView = new maps.SuggestView('delivery_address', {
                    results: 5,
                    provider: {
                        suggest: (request, options) => {
                            return maps.suggest('Владикавказ, ' + request);
                        }
                    }
                });

                console.log('Подсказки адресов инициализированы');

                // Обработчик выбора подсказки
                suggestView.events.add('select', function (e) {
                    const selectedItem = e.get('item');
                    console.log('Выбран адрес:', selectedItem.value);
                });

            } catch (error) {
                console.error('Ошибка при инициализации подсказок:', error);
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке API:', error);
        });
});
