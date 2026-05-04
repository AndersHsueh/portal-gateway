const API_BASE = '/api';

// 认证相关
async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('email', email);
  formData.append('password', password);

  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '登录失败');
  }

  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  return data;
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  window.location.reload();
}

function getCurrentUser() {
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}

function getToken() {
  return localStorage.getItem('token');
}

function isLoggedIn() {
  return !!getToken();
}

function isAdmin() {
  const user = getCurrentUser();
  return user && user.role === 'admin';
}

async function fetchWithAuth(url, options = {}) {
  const token = getToken();
  const headers = {
    ...options.headers
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    logout();
    throw new Error('未登录或登录已过期');
  }

  return response;
}

// 用户管理 API
async function getUsers() {
  const response = await fetchWithAuth(`${API_BASE}/admin/users`);
  return response.json();
}

async function createUser(email, password, name, role = 'user') {
  const response = await fetchWithAuth(`${API_BASE}/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name, role })
  });
  return response.json();
}

async function updateUser(userId, data) {
  const response = await fetchWithAuth(`${API_BASE}/admin/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return response.json();
}

async function deleteUser(userId) {
  const response = await fetchWithAuth(`${API_BASE}/admin/users/${userId}`, {
    method: 'DELETE'
  });
  return response.json();
}

async function resetPassword(userId, newPassword) {
  const response = await fetchWithAuth(`${API_BASE}/admin/users/${userId}/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_password: newPassword })
  });
  return response.json();
}

// 登录日志
async function getLogs(skip = 0, limit = 50) {
  const response = await fetchWithAuth(`${API_BASE}/admin/logs?skip=${skip}&limit=${limit}`);
  return response.json();
}

// 项目列表
async function getProjects() {
  const response = await fetchWithAuth(`${API_BASE}/projects`);
  return response.json();
}

window.API = {
  login, logout, getCurrentUser, isLoggedIn, isAdmin,
  getUsers, createUser, updateUser, deleteUser, resetPassword,
  getLogs, getProjects
};