// Configuration
const API_BASE_URL = 'https://your-railway-app.up.railway.app'; // Will update after deployment

// State management
let currentUser = null;
let authToken = null;
let dataInterval = null;

// DOM Elements
const loginScreen = document.getElementById('loginScreen');
const registerScreen = document.getElementById('registerScreen');
const dashboard = document.getElementById('dashboard');

// Utility Functions
function showAlert(elementId, message, type) {
    const alert = document.getElementById(elementId);
    alert.textContent = message;
    alert.className = `alert ${type} show`;
    setTimeout(() => {
        alert.classList.remove('show');
    }, 5000);
}

function setScreen(screen) {
    loginScreen.classList.remove('active');
    registerScreen.classList.remove('active');
    dashboard.classList.remove('active');
    screen.classList.add('active');
}

// Authentication Functions
async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    if (!username || !password) {
        showAlert('loginAlert', 'Please enter both username and password', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
        });

        const data = await response.json();

        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            document.getElementById('userDisplay').textContent = `Welcome, ${currentUser.full_name}`;
            setScreen(dashboard);
            startDataUpdates();
        } else {
            showAlert('loginAlert', data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        showAlert('loginAlert', 'Network error. Please try again.', 'error');
    }
}

async function register() {
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const fullName = document.getElementById('regFullName').value;
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('regConfirm').value;

    if (!username || !email || !fullName || !password || !confirm) {
        showAlert('registerAlert', 'Please fill all fields', 'error');
        return;
    }

    if (password !== confirm) {
        showAlert('registerAlert', 'Passwords do not match', 'error');
        return;
    }

    if (password.length < 6) {
        showAlert('registerAlert', 'Password must be at least 6 characters', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password, full_name: fullName }),
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('registerAlert', 'Registration successful! Please login.', 'success');
            setTimeout(() => showLogin(), 2000);
        } else {
            showAlert('registerAlert', data.detail || 'Registration failed', 'error');
        }
    } catch (error) {
        showAlert('registerAlert', 'Network error. Please try again.', 'error');
    }
}

function logout() {
    authToken = null;
    currentUser = null;
    if (dataInterval) {
        clearInterval(dataInterval);
    }
    setScreen(loginScreen);
}

function showRegister() {
    setScreen(registerScreen);
}

function showLogin() {
    setScreen(loginScreen);
}

// Grid Data Functions
async function fetchGridData() {
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE_URL}/grid/current`, {
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (response.ok) {
            const data = await response.json();
            updateDashboard(data);
        }
    } catch (error) {
        console.error('Error fetching grid data:', error);
    }
}

async function setScenario(scenario) {
    if (!authToken) return;

    try {
        const response = await fetch(`${API_BASE_URL}/grid/scenario/${scenario}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
            },
        });

        if (response.ok) {
            const data = await response.json();
            updateDashboard(data.data);
            showAlert('alertBanner', `Scenario changed to ${scenario.toUpperCase()}`, 'success');
        }
    } catch (error) {
        console.error('Error setting scenario:', error);
    }
}

function startDataUpdates() {
    // Initial data fetch
    fetchGridData();
    
    // Set up interval for updates (every 2 seconds)
    dataInterval = setInterval(fetchGridData, 2000);
}

// Dashboard Update Functions
function updateDashboard(data) {
    // Update metric values
    document.getElementById('frequencyValue').textContent = `${data.frequency} Hz`;
    document.getElementById('loadValue').textContent = `${data.load_demand} MW`;
    document.getElementById('generationValue').textContent = `${data.total_generation} MW`;
    document.getElementById('socValue').textContent = `${data.bess_soc}%`;

    // Update status colors
    updateStatusColors(data);

    // Update charts
    updateFrequencyGauge(data.frequency);
    updateBatteryGauge(data.bess_soc);
    updateGenerationChart(data);
}

function updateStatusColors(data) {
    const frequencyCard = document.getElementById('frequencyCard');
    const socCard = document.getElementById('socCard');
    const frequencyValue = document.getElementById('frequencyValue');
    const socValue = document.getElementById('socValue');

    // Frequency status
    const freqDeviation = Math.abs(data.frequency - 50);
    if (freqDeviation > 0.3) {
        frequencyCard.style.borderColor = 'var(--digital-red)';
        frequencyValue.className = 'metric-value status-critical';
    } else if (freqDeviation > 0.2) {
        frequencyCard.style.borderColor = 'var(--digital-yellow)';
        frequencyValue.className = 'metric-value status-warning';
    } else {
        frequencyCard.style.borderColor = 'var(--digital-green)';
        frequencyValue.className = 'metric-value status-normal';
    }

    // BESS status
    if (data.bess_soc >= 100) {
        socCard.style.borderColor = 'var(--digital-blue)';
        socValue.className = 'metric-value';
    } else if (data.bess_soc <= 0) {
        socCard.style.borderColor = 'var(--digital-red)';
        socValue.className = 'metric-value status-critical';
    } else if (data.bess_soc < 20) {
        socCard.style.borderColor = 'var(--digital-yellow)';
        socValue.className = 'metric-value status-warning';
    } else {
        socCard.style.borderColor = 'var(--digital-green)';
        socValue.className = 'metric-value status-normal';
    }
}

function updateFrequencyGauge(frequency) {
    const freqColor = Math.abs(frequency - 50) > 0.3 ? '#ff003c' : 
                     Math.abs(frequency - 50) > 0.2 ? '#ffdd00' : '#00ff41';

    const data = [{
        type: "indicator",
        mode: "gauge+number+delta",
        value: frequency,
        delta: { reference: 50 },
        gauge: {
            axis: { range: [49, 51], tickwidth: 1, tickcolor: "white" },
            bar: { color: freqColor },
            bgcolor: "rgba(0,0,0,0)",
            borderwidth: 2,
            bordercolor: "gray",
            steps: [
                { range: [49, 49.8], color: 'rgba(255,0,60,0.3)' },
                { range: [49.8, 50.2], color: 'rgba(0,255,65,0.3)' },
                { range: [50.2, 51], color: 'rgba(255,0,60,0.3)' }
            ]
        }
    }];

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'white', family: 'Roboto Mono' },
        margin: { t: 50, b: 20, l: 20, r: 20 },
        height: 250
    };

    Plotly.react('frequencyGauge', data, layout);
}

function updateBatteryGauge(soc) {
    const socColor = soc > 50 ? '#00ff41' : soc > 20 ? '#ffdd00' : '#ff003c';

    const data = [{
        type: "indicator",
        mode: "gauge+number",
        value: soc,
        gauge: {
            axis: { range: [0, 100] },
            bar: { color: socColor },
            bgcolor: "rgba(0,0,0,0)",
            borderwidth: 2,
            bordercolor: "gray",
            steps: [
                { range: [0, 20], color: 'rgba(255,0,60,0.3)' },
                { range: [20, 50], color: 'rgba(255,221,0,0.3)' },
                { range: [50, 100], color: 'rgba(0,255,65,0.3)' }
            ]
        }
    }];

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'white', family: 'Roboto Mono' },
        margin: { t: 50, b: 20, l: 20, r: 20 },
        height: 250
    };

    Plotly.react('batteryGauge', data, layout);
}

function updateGenerationChart(data) {
    const chartData = [{
        values: [data.geothermal, data.hydro, data.wind, data.solar, data.thermal],
        labels: ['Geothermal', 'Hydro', 'Wind', 'Solar', 'Thermal'],
        type: 'pie',
        marker: {
            colors: ['#00a8ff', '#00ff41', '#9d4edd', '#ffdd00', '#ff7b00']
        },
        textinfo: 'percent+label',
        textposition: 'inside',
        textfont: { color: 'white', family: 'Roboto Mono' }
    }];

    const layout = {
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: 'white', family: 'Roboto Mono' },
        margin: { t: 50, b: 20, l: 20, r: 20 },
        height: 250,
        showlegend: false
    };

    Plotly.react('generationChart', chartData, layout);
}

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already logged in (from localStorage)
    const savedToken = localStorage.getItem('authToken');
    const savedUser = localStorage.getItem('currentUser');
    
    if (savedToken && savedUser) {
        authToken = savedToken;
        currentUser = JSON.parse(savedUser);
        document.getElementById('userDisplay').textContent = `Welcome, ${currentUser.full_name}`;
        setScreen(dashboard);
        startDataUpdates();
    } else {
        setScreen(loginScreen);
    }

    // Save auth data when logging in
    if (authToken && currentUser) {
        localStorage.setItem('authToken', authToken);
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
    }
});

// Clear storage on logout
function logout() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    authToken = null;
    currentUser = null;
    if (dataInterval) {
        clearInterval(dataInterval);
    }
    setScreen(loginScreen);
}
