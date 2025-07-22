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
const authOverlay = document.querySelector('.auth.vert_center');

// Lottie Animations
if (installationIcon) {
    lottie.loadAnimation({
        container: installationIcon,
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: '/static/success.json'
    });
}
if (authOverlay) {
    lottie.loadAnimation({
        container: document.getElementById('tg_icon'),
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: '/static/telegram.json'
    });
}

// Functions
function updateProgressBar() {
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach(step => {
        const stepNum = parseInt(step.getAttribute('data-step'));
        step.classList.toggle('active', stepNum <= currentStep);
    });
}

function showStep(stepNumber) {
    document.querySelectorAll('.wizard-step').forEach(step => step.classList.remove('active'));
    const nextStep = document.getElementById(`step-${stepNumber}`);
    if (nextStep) nextStep.classList.add('active');
    currentStep = stepNumber;
    updateProgressBar();
    updateNavigation();
}

function updateNavigation() {
    backBtn.style.display = currentStep > 1 && currentStep < totalSteps ? 'inline-flex' : 'none';
    nextBtn.style.display = currentStep === 3 ? 'inline-flex' : 'none';
    
    if (currentStep === 2) {
         backBtn.style.display = 'inline-flex';
    }
}

function reauthenticateAndStart() {
    console.log("Starting re-authentication...");
    authOverlay.style.display = 'flex';
    fetch("/web_auth", { method: "POST", credentials: "include" })
        .then(response => response.text())
        .then(response => {
            authOverlay.style.display = 'none';
            if (response === "TIMEOUT") {
                Swal.fire('Тайм-аут', 'Вы не подтвердили вход в Telegram.', 'error');
            } else {
                console.log("Re-authentication successful, moving to step 2.");
                $.cookie("session", response, { expires: 1, path: '/' });
                showStep(2);
            }
        })
        .catch(error => {
            authOverlay.style.display = 'none';
            Swal.fire('Ошибка', `Не удалось выполнить аутентификацию: ${error}`, 'error');
        });
}


function handlePhoneSubmission() {
    if (phone_hash) {
        if (document.getElementById('block_2fa').style.display !== 'none') {
            submit2FA();
        } else {
            submitCode();
        }
    } else {
        submitPhone();
    }
}

function submitPhone() {
    const phone = phoneInput.value;
    if (!phone) {
        Swal.fire('Ошибка', 'Пожалуйста, введите номер телефона.', 'error');
        return;
    }
    
    nextBtn.innerHTML = '<div class="vert_center">Загрузка...</div>';
    nextBtn.disabled = true;

    fetch("/send_tg_code", { method: "POST", body: phone, credentials: "include" })
        .then(response => {
            if (response.status === 200) {
                document.getElementById('block_phone').style.display = 'none';
                document.getElementById('block_code').style.display = 'block';
                Swal.fire('Успех', 'Код отправлен в Telegram!', 'success');
                phone_hash = "set";
            } else {
                return response.text().then(text => Promise.reject(text));
            }
        })
        .catch(error => {
            Swal.fire('Ошибка', `Не удалось отправить код: ${error}`, 'error');
        })
        .finally(() => {
            nextBtn.innerHTML = '<div class="vert_center">Далее</div>';
            nextBtn.disabled = false;
        });
}

function submitCode() {
    const code = codeInput.value;
    if (!code) {
        Swal.fire('Ошибка', 'Пожалуйста, введите код подтверждения.', 'error');
        return;
    }
    
    nextBtn.innerHTML = '<div class="vert_center">Проверка...</div>';
    nextBtn.disabled = true;

    fetch("/tg_code", { method: "POST", body: code + "\n" + phoneInput.value, credentials: "include" })
        .then(response => {
            if (response.status === 200) {
                 finishLogin();
            } else if (response.status === 401) {
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
            nextBtn.innerHTML = '<div class="vert_center">Далее</div>';
            nextBtn.disabled = false;
        });
}

function submit2FA() {
    const password = passwordInput.value;
    if (!password) {
        Swal.fire('Ошибка', 'Пожалуйста, введите пароль 2FA.', 'error');
        return;
    }

    nextBtn.innerHTML = '<div class="vert_center">Вход...</div>';
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
            nextBtn.innerHTML = '<div class="vert_center">Далее</div>';
            nextBtn.disabled = false;
        });
}

function finishLogin() {
    showStep(4);
    fetch("/finish_login", { method: "POST", credentials: "include" })
        .catch(error => {
            console.error('Finish login call failed, but proceeding with UI. Error:', error);
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
            if (response.status === 200) {
                clearInterval(qrTask);
                finishLogin();
            } else if (response.status === 403) {
                clearInterval(qrTask);
                promptQr2FA();
            } else if (response.status === 201) {
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

// Initial state and event listeners
document.addEventListener('DOMContentLoaded', () => {
    startBtn.addEventListener('click', () => {
        console.log("Start button clicked. tg_done:", tg_done);
        if (tg_done) {
            reauthenticateAndStart();
        } else {
            showStep(2);
        }
    });

    showStep(1);
    if (tg_done) {
        document.querySelector("#start-btn .vert_center").innerText = 'Добавить аккаунт';
    }
});