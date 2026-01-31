function toggleNotifications(event) {
    if (event) {
        event.stopPropagation();
    }
    
    const panel = document.getElementById('notificationsPanel');
    if (!panel) {
        console.error('Панель уведомлений не найдена');
        return;
    }
    
    if (panel.style.display === 'block') {
        panel.style.display = 'none';
    } else {
        panel.style.display = 'block';
        loadNotifications();
    }
}

function loadNotifications() {
    fetch('/get_notifications')
    .then(response => {
        if (!response.ok) {
            throw new Error('Ошибка загрузки уведомлений');
        }
        return response.json();
    })
    .then(data => {
        const container = document.querySelector('.notifications-list');
        if (!container) {
            console.error('Контейнер уведомлений не найден');
            return;
        }
        
        if (data.notifications && data.notifications.length > 0) {
            container.innerHTML = data.notifications.map(notification => `
                <div class="notification-item ${notification.is_read ? '' : 'unread'}" 
                     onclick="markAsRead(${notification.id}, this)">
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-date">${formatNotificationDate(notification.created_at)}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="notification-item">Нет уведомлений</div>';
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки уведомлений:', error);
        const container = document.querySelector('.notifications-list');
        if (container) {
            container.innerHTML = '<div class="notification-item">Ошибка загрузки</div>';
        }
    });
}

function markAsRead(notificationId, element) {
    if (element) {
        element.classList.remove('unread');
    }
    
    fetch('/mark_notification_read', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({notification_id: notificationId})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                const count = parseInt(badge.textContent) - 1;
                if (count > 0) {
                    badge.textContent = count;
                } else {
                    badge.remove();
                }
            }
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
    });
}

function markAllAsRead() {
    fetch('/mark_all_notifications_read', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const unreadItems = document.querySelectorAll('.notification-item.unread');
            unreadItems.forEach(item => {
                item.classList.remove('unread');
            });
            
            const badge = document.querySelector('.notification-badge');
            if (badge) {
                badge.remove();
            }
            
            loadNotifications();
        }
    })
    .catch(error => {
        console.error('Ошибка отметки всех уведомлений:', error);
    });
}

function formatNotificationDate(dateString) {
    if (!dateString) return 'Дата не указана';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffMinutes = Math.floor(diffTime / (1000 * 60));
        const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffMinutes < 1) return 'Только что';
        if (diffMinutes < 60) return `${diffMinutes} мин. назад`;
        if (diffHours < 24) return `${diffHours} ч. назад`;
        if (diffDays === 1) return 'Вчера';
        if (diffDays < 7) return `${diffDays} дн. назад`;
        
        return date.toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'long',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (error) {
        return 'Дата не указана';
    }
}

function showSection(sectionName, buttonElement) {
    console.log('Переключаем на секцию:', sectionName);

    const sections = document.querySelectorAll('.section-content');
    sections.forEach(section => {
        section.style.display = 'none';
    });
    
    const buttons = document.querySelectorAll('.category-btn');
    buttons.forEach(btn => {
        btn.classList.remove('active');
    });
    
    const targetSection = document.getElementById(sectionName + '-section');
    if (targetSection) {
        targetSection.style.display = 'block';
        console.log('Секция показана:', targetSection.id);
        
        if (sectionName === 'requests') {
            console.log('Загружаем заявки учителя...');
            setTimeout(loadTeacherRequests, 100);
        }
    } else {
        console.error('Секция не найдена:', sectionName + '-section');
    }
    
    if (buttonElement) {
        buttonElement.classList.add('active');
    }
}

function requestEquipment(equipmentId) {
    console.log('=== ЗАПРОС ОБОРУДОВАНИЯ ===');
    console.log('equipmentId:', equipmentId, 'type:', typeof equipmentId);
    
    if (!equipmentId || equipmentId === 'undefined' || equipmentId === 'null') {
        alert('ОШИБКА: ID оборудования не определен');
        return;
    }
    
    equipmentId = parseInt(equipmentId);
    if (isNaN(equipmentId) || equipmentId <= 0) {
        alert('ОШИБКА: Неверный ID оборудования: ' + equipmentId);
        return;
    }
    
    if (!confirm(`Подать заявку на оборудование ID: ${equipmentId}?`)) return;
    
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = 'ОБРАБОТКА...';
    button.disabled = true;
    
    console.log('Отправка запроса для equipmentId:', equipmentId);
    
    const formData = new FormData();
    formData.append('equipment_id', equipmentId.toString());
    
    fetch('/request_equipment', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) throw new Error('HTTP ' + response.status);
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.success) {
            alert('Заявка подана успешно!');
            location.reload();
        } else {
            throw new Error(data.error || 'Неизвестная ошибка');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка: ' + error.message);
        button.textContent = originalText;
        button.disabled = false;
    });
}

// ===== ФУНКЦИИ ДЛЯ УЧИТЕЛЯ =====
function loadTeacherRequests() {
    console.log('=== ЗАГРУЗКА ЗАЯВОК УЧИТЕЛЯ ===');
    const container = document.getElementById('teacher-requests-list');
    if (!container) {
        console.error('Контейнер заявок не найден');
        return;
    }

    container.innerHTML = '<div class="loading">Загрузка заявок...</div>';

    fetch('/teacher_requests')
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ошибка: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Получены заявки:', data);
        
        if (data.success && data.requests && data.requests.length > 0) {
            let html = '';
            data.requests.forEach(request => {
                console.log('Обработка заявки:', request);
                
                let actionsHTML = '';
                const canApprove = request.status === 'pending' && request.equipment_available > 0;
                
                if (request.status === 'pending') {
                    actionsHTML = `
                        <div class="teacher-actions">
                            <button class="action-btn btn-approve" 
                                    onclick="approveRequest(${request.id})"
                                    ${!canApprove ? 'disabled title="Оборудование недоступно"' : ''}>
                                ОДОБРИТЬ
                            </button>
                            <button class="action-btn btn-reject" 
                                    onclick="rejectRequest(${request.id})">
                                ОТКЛОНИТЬ
                            </button>
                        </div>
                    `;
                } else if (request.status === 'approved') {
                    actionsHTML = `
                        <div class="teacher-actions">
                            <button class="action-btn btn-return" 
                                    onclick="returnRequest(${request.id})">
                                ОТМЕТИТЬ ВОЗВРАТ
                            </button>
                        </div>
                    `;
                }
                
                html += `
                    <div class="request-item">
                        <div class="request-header">
                            <h3>${request.equipment_name || 'Неизвестное оборудование'}</h3>
                            <span class="request-status status-${request.status || 'pending'}">
                                ${getStatusText(request.status)}
                            </span>
                        </div>
                        <p><strong>Ученик:</strong> ${request.student_name || 'Неизвестный'}</p>
                        <p><strong>Класс:</strong> ${request.student_class || 'Не указан'}</p>
                        <p><strong>Дата заявки:</strong> ${request.request_date || 'Не указана'}</p>
                        ${request.due_date ? `<p><strong>Вернуть до:</strong> ${request.due_date}</p>` : ''}
                        ${request.status === 'pending' ? `<p><strong>Доступно единиц:</strong> ${request.equipment_available || 0}</p>` : ''}
                        ${actionsHTML}
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="no-requests">Нет активных заявок от учеников</div>';
        }
    })
    .catch(error => {
        console.error('Ошибка загрузки заявок:', error);
        container.innerHTML = '<div class="error">Ошибка загрузки заявок. Попробуйте обновить страницу.</div>';
    });
}

function approveRequest(requestId) {
    console.log('=== ОДОБРЕНИЕ ЗАЯВКИ ===', requestId);
    
    // Рассчитываем дату на 7 дней вперед
    const today = new Date();
    const dueDate = new Date(today);
    dueDate.setDate(today.getDate() + 7);
    
    const year = dueDate.getFullYear();
    const month = String(dueDate.getMonth() + 1).padStart(2, '0');
    const day = String(dueDate.getDate()).padStart(2, '0');
    const defaultDueDate = `${year}-${month}-${day}`;
    
    // Создаем модальное окно для ввода даты
    const modalHtml = `
        <div id="dateModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        ">
            <div style="
                background: white;
                padding: 30px;
                border-radius: 10px;
                width: 90%;
                max-width: 400px;
            ">
                <h3 style="margin-top: 0;">Укажите дату возврата</h3>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 5px; font-weight: bold;">
                        Дата возврата (ГГГГ-ММ-ДД):
                    </label>
                    <input type="date" 
                           id="dueDateInput" 
                           value="${defaultDueDate}"
                           style="
                               width: 100%;
                               padding: 10px;
                               border: 2px solid #ddd;
                               border-radius: 5px;
                               font-size: 16px;
                           "
                           min="${new Date().toISOString().split('T')[0]}">
                </div>
                <div style="display: flex; gap: 10px;">
                    <button onclick="document.getElementById('dateModal').remove()"
                            style="
                                flex: 1;
                                padding: 10px;
                                background: #6c757d;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                cursor: pointer;
                            ">
                        ОТМЕНА
                    </button>
                    <button onclick="submitApprove(${requestId})"
                            style="
                                flex: 1;
                                padding: 10px;
                                background: #28a745;
                                color: white;
                                border: none;
                                border-radius: 5px;
                                cursor: pointer;
                            ">
                        ОДОБРИТЬ
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

function submitApprove(requestId) {
    const dueDateInput = document.getElementById('dueDateInput');
    const dueDate = dueDateInput ? dueDateInput.value : '';
    
    if (!dueDate) {
        alert('Пожалуйста, укажите дату возврата');
        return;
    }
    
    // Удаляем модальное окно
    const modal = document.getElementById('dateModal');
    if (modal) modal.remove();
    
    updateRequestStatus(requestId, 'approved', dueDate);
}

function rejectRequest(requestId) {
    console.log('=== ОТКЛОНЕНИЕ ЗАЯВКИ ===', requestId);
    if (confirm('Вы уверены, что хотите отклонить эту заявку?')) {
        updateRequestStatus(requestId, 'rejected');
    }
}

function returnRequest(requestId) {
    console.log('=== ОТМЕТКА ВОЗВРАТА ===', requestId);
    if (confirm('Отметить оборудование как возвращенное?')) {
        updateRequestStatus(requestId, 'returned');
    }
}

function updateRequestStatus(requestId, status, dueDate = null) {
    console.log('=== ОБНОВЛЕНИЕ СТАТУСА ===', {requestId, status, dueDate});
    
    const formData = new FormData();
    formData.append('request_id', requestId.toString());
    formData.append('status', status);
    
    if (dueDate) {
        formData.append('due_date', dueDate);
    }

    // Показать индикатор загрузки
    const button = event ? event.target : null;
    if (button) {
        const originalText = button.textContent;
        button.textContent = 'ОБРАБОТКА...';
        button.disabled = true;
    }

    fetch('/update_request_status', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP ошибка: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.success) {
            alert('Статус заявки успешно обновлен!');
            // Обновляем список заявок
            loadTeacherRequests();
        } else {
            alert(`Ошибка: ${data.error || 'Неизвестная ошибка'}`);
            if (button) {
                button.textContent = originalText;
                button.disabled = false;
            }
        }
    })
    .catch(error => {
        console.error('Ошибка сети:', error);
        alert('Ошибка сети. Проверьте подключение к интернету.');
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
    });
}

function getStatusText(status) {
    const statusMap = {
        'pending': 'ОЖИДАЕТ РАССМОТРЕНИЯ',
        'approved': 'ОДОБРЕНО', 
        'rejected': 'ОТКЛОНЕНО',
        'returned': 'ВОЗВРАЩЕНО'
    };
    return statusMap[status] || status.toUpperCase();
}

// ФУНКЦИИ ДЛЯ ДОБАВЛЕНИЯ ОБОРУДОВАНИЯ

function showAddEquipmentForm() {
    document.getElementById('addEquipmentModal').style.display = 'flex';
}

function hideAddEquipmentForm() {
    document.getElementById('addEquipmentModal').style.display = 'none';
}

// ФУНКЦИИ ДЛЯ СТРАНИЦЫ АККАУНТА

function openProfileModal() {
    document.getElementById('profileModal').style.display = 'block';
}

function closeProfileModal() {
    document.getElementById('profileModal').style.display = 'none';
}

// ИНИЦИАЛИЗАЦИЯ ПРИ ЗАГРУЗКЕ СТРАНИЦЫ

document.addEventListener('DOMContentLoaded', function() {
    console.log('Инициализация JavaScript...');
    
    const orderButtons = document.querySelectorAll('.order-button:not(.disabled)');
    orderButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const equipmentId = this.getAttribute('data-equipment-id');
            
            if (!equipmentId) {
                alert('Ошибка: ID оборудования не определен');
                return;
            }
            
            if (!confirm('Подать заявку на это оборудование?')) return;
            
            const originalText = this.textContent;
            this.textContent = 'ОБРАБОТКА...';
            this.disabled = true;
            
            const formData = new FormData();
            formData.append('equipment_id', equipmentId);
            
            fetch('/request_equipment', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Заявка подана успешно!');
                    location.reload();
                } else {
                    alert('Ошибка: ' + data.error);
                    this.textContent = originalText;
                    this.disabled = false;
                }
            })
            .catch(error => {
                alert('Ошибка сети');
                this.textContent = originalText;
                this.disabled = false;
            });
        });
    });
    
    const equipmentForm = document.getElementById('addEquipmentForm');
    if (equipmentForm) {
        equipmentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.textContent = 'ДОБАВЛЯЕМ...';
            
            const formData = new FormData(this);
            
            fetch('/add_equipment', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Оборудование добавлено!');
                    hideAddEquipmentForm();
                    location.reload();
                } else {
                    alert('Ошибка: ' + data.error);
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'ДОБАВИТЬ';
                }
            })
            .catch(error => {
                alert('Ошибка сети');
                submitBtn.disabled = false;
                submitBtn.textContent = 'ДОБАВИТЬ';
            });
        });
    }
    
    const modal = document.getElementById('addEquipmentModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                hideAddEquipmentForm();
            }
        });
    }
    
    const profileModal = document.getElementById('profileModal');
    if (profileModal) {
        window.onclick = function(event) {
            if (event.target === profileModal) {
                closeProfileModal();
            }
        }
        
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                
                fetch('/update_profile', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.text())
                .then(data => {
                    if (data === 'Профиль обновлен') {
                        alert('Профиль обновлен!');
                        closeProfileModal();
                        location.reload();
                    } else {
                        alert('Ошибка: ' + data);
                    }
                })
                .catch(error => {
                    alert('Произошла ошибка');
                });
            });
        }
    }
    
    const images = document.querySelectorAll('.equipment-image');
    images.forEach(img => {
        img.addEventListener('error', function() {
            this.src = '/static/images/placeholder.jpg';
        });
    });
    
    console.log('JavaScript инициализирован');
});