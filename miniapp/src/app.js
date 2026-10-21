// Focus Telegram Mini App Client

const API_BASE = window.location.origin;
const tg = window.Telegram?.WebApp;

// Init WebApp
if (tg) {
  tg.ready();
  tg.expand();
}

let currentFilter = 'all';
let cachedTasks = [];
let cachedHabits = [];

// Helper for authenticated requests
async function apiRequest(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  // Attach Telegram initData if available
  if (tg?.initData) {
    headers['X-Telegram-Init-Data'] = tg.initData;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData?.error?.message || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn(`API request to ${endpoint} failed:`, err);
    return null;
  }
}

// Switch Bottom Tabs
function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  const navItems = document.querySelectorAll('.nav-item');
  const tabNames = ['today', 'tasks', 'habits', 'stats', 'settings'];
  const idx = tabNames.indexOf(tabId);
  if (idx !== -1 && navItems[idx]) {
    navItems[idx].classList.add('active');
  }

  if (tabId === 'today') loadToday();
  if (tabId === 'tasks') loadTasks();
  if (tabId === 'habits') loadHabits();
  if (tabId === 'stats') loadStats();
}

// ── Load Today Overview ───────────────────────────────────────────────────

async function loadToday() {
  const data = await apiRequest('/api/v1/today');
  if (!data) {
    renderFallbackToday();
    return;
  }

  document.getElementById('today-tasks-count').textContent = `${data.completed_today}/${data.total_today}`;
  document.getElementById('today-focus-mins').textContent = `${data.focus_minutes_today} мин`;
  document.getElementById('today-habits-count').textContent = data.habits.length;

  // Render today tasks
  const container = document.getElementById('today-tasks-list');
  if (!data.tasks.length) {
    container.innerHTML = '<div class="empty-state">Нет задач на сегодня 🎉</div>';
  } else {
    container.innerHTML = data.tasks.map(t => renderTaskItem(t)).join('');
  }

  // Render today habits
  const hContainer = document.getElementById('today-habits-list');
  if (!data.habits.length) {
    hContainer.innerHTML = '<div class="empty-state">Нет привычек на сегодня</div>';
  } else {
    hContainer.innerHTML = data.habits.map(h => renderHabitItem(h)).join('');
  }
}

function renderTaskItem(task) {
  const isDone = task.status === 'completed';
  return `
    <div class="task-item">
      <div class="task-check ${isDone ? 'completed' : ''}" onclick="toggleTaskStatus(${task.id}, '${task.status}')">
        ${isDone ? '✓' : ''}
      </div>
      <div class="task-info">
        <div class="task-title ${isDone ? 'completed' : ''}">${escapeHtml(task.title)}</div>
        <div class="task-meta">${task.category || 'Общее'} • ${task.priority || 'medium'}</div>
      </div>
    </div>
  `;
}

function renderHabitItem(habit) {
  const isDone = habit.completed_today;
  return `
    <div class="habit-item">
      <div class="habit-check ${isDone ? 'completed' : ''}" onclick="completeHabit(${habit.id})">
        ${isDone ? '✓' : ''}
      </div>
      <div class="habit-info">
        <div class="task-title">${escapeHtml(habit.title)}</div>
        <div class="task-meta">🔥 Серия: ${habit.current_streak} дн. (лучшая: ${habit.best_streak})</div>
      </div>
    </div>
  `;
}

// ── Load Tasks Tab ────────────────────────────────────────────────────────

async function loadTasks() {
  const data = await apiRequest('/api/v1/tasks');
  const container = document.getElementById('all-tasks-list');

  if (!data || !data.tasks) {
    renderFallbackTasks();
    return;
  }

  cachedTasks = data.tasks;
  renderFilteredTasks();
}

function filterTasks(type) {
  currentFilter = type;
  document.querySelectorAll('.filter-pills .pill').forEach(el => el.classList.remove('active'));
  event.target.classList.add('active');
  renderFilteredTasks();
}

function renderFilteredTasks() {
  const container = document.getElementById('all-tasks-list');
  let filtered = cachedTasks;

  if (currentFilter === 'today') {
    const todayStr = new Date().toISOString().split('T')[0];
    filtered = cachedTasks.filter(t => t.due_date === todayStr);
  } else if (currentFilter === 'high') {
    filtered = cachedTasks.filter(t => t.priority === 'high' || t.priority === 'urgent');
  } else if (currentFilter === 'completed') {
    filtered = cachedTasks.filter(t => t.status === 'completed');
  } else {
    filtered = cachedTasks.filter(t => t.status !== 'completed');
  }

  if (!filtered.length) {
    container.innerHTML = '<div class="empty-state">Нет задач в этой категории</div>';
    return;
  }

  container.innerHTML = filtered.map(t => renderTaskItem(t)).join('');
}

async function quickCreateTask() {
  const input = document.getElementById('new-task-input');
  const text = input.value.trim();
  if (!text) return;

  const created = await apiRequest('/api/v1/tasks', {
    method: 'POST',
    body: JSON.stringify({ title: text, priority: 'medium' })
  });

  input.value = '';
  if (created) {
    cachedTasks.unshift(created);
    renderFilteredTasks();
  }
}

async function toggleTaskStatus(taskId, currentStatus) {
  const newStatus = currentStatus === 'completed' ? 'in_progress' : 'completed';
  await apiRequest(`/api/v1/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: newStatus })
  });
  // Refresh current view
  loadToday();
  loadTasks();
}

// ── Load Habits Tab ───────────────────────────────────────────────────────

async function loadHabits() {
  const data = await apiRequest('/api/v1/habits');
  const container = document.getElementById('all-habits-list');

  if (!data || !data.length) {
    container.innerHTML = '<div class="empty-state">Привычек пока нет. Нажмите «Добавить»!</div>';
    return;
  }

  cachedHabits = data;
  container.innerHTML = data.map(h => renderHabitItem(h)).join('');
}

async function completeHabit(habitId) {
  await apiRequest(`/api/v1/habits/${habitId}/complete`, {
    method: 'POST',
    body: JSON.stringify({})
  });
  loadToday();
  loadHabits();
}

// ── Load Stats Tab ────────────────────────────────────────────────────────

async function loadStats() {
  const data = await apiRequest('/api/v1/stats');
  if (!data) return;

  document.getElementById('stats-tasks-completed').textContent = data.tasks_completed;
  const mins = data.focus_week?.total_minutes || 0;
  document.getElementById('stats-focus-total').textContent = `${Math.round(mins / 60)} ч`;
  document.getElementById('stats-habits-week').textContent = data.habits_week_completions;
  document.getElementById('stats-overdue-count').textContent = data.tasks_overdue;
  document.getElementById('tier-badge').textContent = (data.subscription_tier || 'FREE').toUpperCase();
}

// Fallback demo renderers for browser preview without backend
function renderFallbackToday() {
  document.getElementById('today-tasks-count').textContent = '2/3';
  document.getElementById('today-focus-mins').textContent = '50 мин';
  document.getElementById('today-habits-count').textContent = '2';

  const container = document.getElementById('today-tasks-list');
  container.innerHTML = `
    <div class="task-item">
      <div class="task-check completed">✓</div>
      <div class="task-info">
        <div class="task-title completed">Подготовить структуру презентации</div>
        <div class="task-meta">Работа • 30 мин</div>
      </div>
    </div>
    <div class="task-item">
      <div class="task-check"></div>
      <div class="task-info">
        <div class="task-title">Согласовать смету с клиентом</div>
        <div class="task-meta">Клиенты • 45 мин 🔴</div>
      </div>
    </div>
  `;

  const hContainer = document.getElementById('today-habits-list');
  hContainer.innerHTML = `
    <div class="habit-item">
      <div class="habit-check completed">✓</div>
      <div class="habit-info">
        <div class="task-title">Читать 20 минут</div>
        <div class="task-meta">🔥 Серия: 7 дн.</div>
      </div>
    </div>
  `;
}

function renderFallbackTasks() {
  cachedTasks = [
    { id: 1, title: 'Подготовить презентацию для клиента', category: 'Работа', priority: 'high', status: 'in_progress' },
    { id: 2, title: 'Записаться на тренировку', category: 'Здоровье', priority: 'medium', status: 'inbox' },
    { id: 3, title: 'Оплатить счета за хостинг', category: 'Финансы', priority: 'urgent', status: 'completed' },
  ];
  renderFilteredTasks();
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Initial boot
document.addEventListener('DOMContentLoaded', () => {
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    document.getElementById('user-name').textContent = u.first_name || 'Пользователь';
  }
  loadToday();
});
