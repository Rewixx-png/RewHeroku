// Global state
let currentStep = 1;
const totalSteps = 4;
let authMethod = ''; // 'phone' or 'qr'
let phone_hash;

// DOM Elements
const wizard = document.getElementById('wizard');
const startBtn = document.getElementById('start-btn');
const backBtn = document.getElementById('back-btn');
const nextBtn = document.getElementById('next-btn');
const authPhoneBtn = document.getElementById('auth-phone-btn');
const authQrBtn = document.getElementById('auth-qr-btn');

const phoneInput = document.getElementById('phone');
const codeInput = document.getElementById('code');
const passwordInput = document.getElementById('password');

const installationIcon = document.getElementById('installation_icon');

// Initialize Lottie animation
if(installationIcon) {
    lottie.loadAnimation({
        container: installationIcon,
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: '/static/success.json'
    });
}


function updateProgressBar() {
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach(step => {
        const stepNum = parseInt(step.getAttribute('data-step'));
        if (stepNum <= currentStep) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
}

function showStep(stepNumber) {
    document.querySelectorAll('.wizard-step').forEach(step => {
        step.classList.remove('active');
    });
    document.getElementById(`step-${stepNumber}`).classList.add('active');
    currentStep = stepNumber;
    updateProgressBar();
    updateNavigation();
}

function updateNavigation() {
    if (currentStep === 1) {
        backBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    } else if (currentStep === 2) {
        backBtn.style.display = 'inline-flex';
        nextBtn.style.display = 'none';
    } else if (currentStep === 3) {
        backBtn.style.display = 'inline-flex';
        nextBtn.style.display = 'inline-flex';
    } else {
        backBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    }
}

// Event Listeners
startBtn.addEventListener('click', () => showStep(2));
backBtn.addEventListener('click', () => {
    if (authMethod === 'qr' && currentStep === 3) {
        if(qrTask) clearInterval(qrTask);
        showStep(2);
    } else if(currentStep > 1) {
       showStep(currentStep - 1);
    }
});

authPhoneBtn.addEventListener('click', () => {
    authMethod = 'phone';
    document.getElementById('phone-auth-content').style.display = 'block';
    document.getElementById('qr-auth-content').style.display = 'none';
    showStep(3);
});

authQrBtn.addEventListener('click', () => {
    authMethod = 'qr';
    document.getElementById('phone-auth-content').style.display = 'none';
    document.getElementById('qr-auth-content').style.display = 'block';
    initQrLogin();
    showStep(3);
});

nextBtn.addEventListener('click', () => {
    if (currentStep === 3 && authMethod === 'phone') {
        handlePhoneSubmission();
    }
});

function handlePhoneSubmission() {
    if (phone_hash) { // We are submitting code or 2FA
        if (document.getElementById('block_2fa').style.display !== 'none') {
            submit2FA();
        } else {
            submitCode();
        }
    } else { // We are submitting phone number
        submitPhone();
    }
}

function submitPhone() {
    const phone = phoneInput.value;
    if (!phone) {
        Swal.fire('Ошибка', 'Пожалуйста, введите номер телефона.', 'error');
        return;
    }
    
    nextBtn.innerText = 'Загрузка...';
    nextBtn.disabled = true;

    fetch("/send_tg_code", { method: "POST", body: phone, credentials: "include" })
        .then(response => {
            if (response.status === 200) {
                document.getElementById('block_phone').style.display = 'none';
                document.getElementById('block_code').style.display = 'block';
                Swal.fire('Успех', 'Код отправлен в Telegram!', 'success');
                phone_hash = "set"; // Mark that we've sent the phone
            } else {
                return response.text().then(text => Promise.reject(text));
            }
        })
        .catch(error => {
            Swal.fire('Ошибка', `Не удалось отправить код: ${error}`, 'error');
        })
        .finally(() => {
            nextBtn.innerText = 'Далее';
            nextBtn.disabled = false;
        });
}

function submitCode() {
    const code = codeInput.value;
    if (!code) {
        Swal.fire('Ошибка', 'Пожалуйста, введите код подтверждения.', 'error');
        return;
    }
    
    nextBtn.innerText = 'Проверка...';
    nextBtn.disabled = true;

    fetch("/tg_code", { method: "POST", body: code + "\n" + phoneInput.value, credentials: "include" })
        .then(response => {
            if (response.status === 200) { // Success
                 finishLogin();
            } else if (response.status === 401) { // 2FA needed
                document.getElementById('block_code').style.display = 'none';
                document.getElementById('block_2fa').style.display = 'block';
                Swal.fire('Внимание', 'Требуется пароль двухфакторной аутентификации.', 'info');
            } else {
                return response.text().then(text => Promise.reject(text));
            }
        })
        .catch(error => {
            Swal.fire('Ошибка', `Неверный код: ${error}`, 'error');
        })
        .finally(() => {
            nextBtn.innerText = 'Далее';
            nextBtn.disabled = false;
        });
}

function submit2FA() {
    const password = passwordInput.value;
    if (!password) {
        Swal.fire('Ошибка', 'Пожалуйста, введите пароль 2FA.', 'error');
        return;
    }

    nextBtn.innerText = 'Вход...';
    nextBtn.disabled = true;

    fetch("/tg_code", { method: "POST", body: codeInput.value + "\n" + phoneInput.value + "\n" + password, credentials: "include" })
        .then(response => {
            if (response.status === 200) {
                finishLogin();
            } else {
                return response.text().then(text => Promise.reject(text));
            }
        })
        .catch(error => {
            Swal.fire('Ошибка', `Неверный пароль: ${error}`, 'error');
        })
        .finally(() => {
            nextBtn.innerText = 'Далее';
            nextBtn.disabled = false;
        });
}

function finishLogin() {
    fetch("/finish_login", { method: "POST", credentials: "include" })
        .then(() => {
            showStep(4);
        })
        .catch(error => {
            Swal.fire('Критическая ошибка', `Не удалось завершить вход: ${error}`, 'error');
        });
}

// QR Code Logic
let qrTask = null;
const qrCode = new QRCodeStyling({
    width: 256,
    height: 256,
    type: "svg",
    dotsOptions: { color: "#000", type: "rounded" },
    backgroundOptions: { color: "transparent" },
    cornersSquareOptions: { color: "#000", type: "extra-rounded" },
    cornersDotOptions: { color: "#000", type: "dot" }
});

function initQrLogin() {
    const qrContainer = document.querySelector("#qr-auth-content .qr_inner");
    qrContainer.innerHTML = '';
    qrCode.append(qrContainer);
    
    fetch("/init_qr_login", { method: "POST", credentials: "include" })
        .then(response => response.text())
        .then(url => {
            qrCode.update({ data: url });
            qrTask = setInterval(pollQrStatus, 2000);
        })
        .catch(error => Swal.fire('Ошибка', `Не удалось инициализировать QR-вход: ${error}`, 'error'));
}

function pollQrStatus() {
    fetch("/get_qr_url", { method: "POST", credentials: "include" })
        .then(response => {
            if (response.status === 200) { // Success
                clearInterval(qrTask);
                finishLogin();
            } else if (response.status === 403) { // 2FA
                clearInterval(qrTask);
                promptQr2FA();
            } else if (response.status === 201) { // Still waiting, new URL
                return response.text().then(url => qrCode.update({ data: url }));
            }
        })
        .catch(error => {
            clearInterval(qrTask);
            Swal.fire('Ошибка', `Ошибка проверки QR-кода: ${error}`, 'error');
        });
}

async function promptQr2FA() {
    const { value: password } = await Swal.fire({
        title: 'Требуется пароль 2FA',
        input: 'password',
        inputLabel: 'Введите ваш пароль двухфакторной аутентификации',
        inputPlaceholder: 'Пароль',
        showCancelButton: true,
        inputValidator: (value) => {
            if (!value) {
                return 'Вы должны ввести пароль!';
            }
        }
    });

    if (password) {
        fetch("/qr_2fa", { method: "POST", body: password, credentials: "include" })
            .then(response => {
                if (response.status === 200) {
                    finishLogin();
                } else {
                    return response.text().then(text => Promise.reject(text));
                }
            })
            .catch(error => Swal.fire('Ошибка', `Неверный пароль: ${error}`, 'error'));
    }
}

// Initial state
document.addEventListener('DOMContentLoaded', () => {
    showStep(1);
    if (tg_done) {
        document.querySelector("#start-btn .vert_center").innerText = 'Добавить аккаунт';
    }
});