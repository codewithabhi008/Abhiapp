/**
 * AbhiApp - Authentication Module
 */

function togglePasswordVisibility(inputId, button) {
  const input = document.getElementById(inputId);
  if (!input) return;
  
  if (input.type === 'password') {
    input.type = 'text';
    button.textContent = '👁️‍🗨️ Hide';
  } else {
    input.type = 'password';
    button.textContent = '👁️ Show';
  }
}

function switchAuthTab(tab) {
  const loginForm = document.getElementById('loginFormContainer');
  const registerForm = document.getElementById('registerFormContainer');
  const loginTabBtn = document.getElementById('tabLoginBtn');
  const registerTabBtn = document.getElementById('tabRegisterBtn');

  if (tab === 'login') {
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
    loginTabBtn.classList.add('active');
    registerTabBtn.classList.remove('active');
  } else {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
    registerTabBtn.classList.add('active');
    loginTabBtn.classList.remove('active');
  }
}

// Handle Login Form Submission
async function handleLoginSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  const errorBox = document.getElementById('authErrorBox');
  errorBox.style.display = 'none';

  const identifier = document.getElementById('loginIdentifier').value.trim();
  const password = document.getElementById('loginPassword').value;
  const remember = document.getElementById('loginRemember').checked;

  if (!identifier || !password) {
    showAuthError('Please enter both username/email and password.');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Authenticating...';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, password, remember })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      window.location.href = data.redirect || '/dashboard';
    } else {
      showAuthError(data.error || 'Authentication failed. Please check credentials.');
    }
  } catch (err) {
    showAuthError('Network error. Unable to reach AbhiApp Vault server.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Sign In to Vault';
  }
}

// Handle Registration Form Submission
async function handleRegisterSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector('button[type="submit"]');
  const errorBox = document.getElementById('authErrorBox');
  errorBox.style.display = 'none';

  const username = document.getElementById('regUsername').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const confirmPassword = document.getElementById('regConfirmPassword').value;

  if (password !== confirmPassword) {
    showAuthError('Passwords do not match.');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Creating Vault Account...';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      window.location.href = data.redirect || '/dashboard';
    } else {
      showAuthError(data.error || 'Registration failed.');
    }
  } catch (err) {
    showAuthError('Network error. Could not connect to vault service.');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Vault Account';
  }
}

function showAuthError(msg) {
  const errorBox = document.getElementById('authErrorBox');
  if (errorBox) {
    errorBox.textContent = msg;
    errorBox.style.display = 'block';
  }
}
