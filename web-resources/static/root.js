$(document).ready(function() {
    // --- Инициализация элементов ---
    const wizard = $('#wizard');
    const steps = $('.wizard-step');
    const progressSteps = $('.progress-step');
    const startBtn = $('#start-btn');
    const nextBtn = $('#next-btn');
    const backBtn = $('#back-btn');
    const addAccountBtn = $('#add-account-btn');
    const authPhoneBtn = $('#auth-phone-btn');
    const authQrBtn = $('#auth-qr-btn');
    const phoneAuthContent = $('#phone-auth-content');
    const qrAuthContent = $('#qr-auth-content');
    const phoneInput = $('#phone');
    const codeInput = $('#code');
    const passwordInput = $('#password');
    const installationIcon = $('#installation_icon');
    const rocketAnimationContainer = document.getElementById('rocket-animation');

    // --- Анимация ракеты Lottie ---
    if (rocketAnimationContainer) {
        lottie.loadAnimation({
            container: rocketAnimationContainer,
            renderer: 'svg',
            loop: true,
            autoplay: true,
            path: 'https://assets2.lottiefiles.com/packages/lf20_p9b31d6d.json' // URL анимации
        });
    }

    // --- Логика воспроизведения музыки ---
    const loudMusic = document.getElementById('loud-music');

    if (loudMusic) {
        const playLoudMusic = () => {
            loudMusic.volume = 1.0;
            loudMusic.currentTime = 0;
            const playPromise = loudMusic.play();
            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    console.error("Ошибка воспроизведения аудио:", error);
                });
            }
        };
        startBtn.on('click', playLoudMusic);
        addAccountBtn.on('click', playLoudMusic);
    }
    
    // --- Анимация фона с частицами ---
    const canvas = document.getElementById('particle-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        let particlesArray;

        class Particle {
            constructor(x, y, directionX, directionY, size, color) {
                this.x = x;
                this.y = y;
                this.directionX = directionX;
                this.directionY = directionY;
                this.size = size;
                this.color = color;
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2, false);
                ctx.fillStyle = this.color;
                ctx.fill();
            }
            update() {
                if (this.x > canvas.width || this.x < 0) {
                    this.directionX = -this.directionX;
                }
                if (this.y > canvas.height || this.y < 0) {
                    this.directionY = -this.directionY;
                }
                this.x += this.directionX;
                this.y += this.directionY;
                this.draw();
            }
        }

        function initParticles() {
            particlesArray = [];
            let numberOfParticles = (canvas.height * canvas.width) / 9000;
            for (let i = 0; i < numberOfParticles; i++) {
                let size = (Math.random() * 2) + 0.5;
                let x = (Math.random() * ((innerWidth - size * 2) - (size * 2)) + size * 2);
                let y = (Math.random() * ((innerHeight - size * 2) - (size * 2)) + size * 2);
                let directionX = (Math.random() * .4) - .2;
                let directionY = (Math.random() * .4) - .2;
                let color = 'rgba(135, 116, 225, 0.3)';
                particlesArray.push(new Particle(x, y, directionX, directionY, size, color));
            }
        }

        function animateParticles() {
            requestAnimationFrame(animateParticles);
            ctx.clearRect(0, 0, innerWidth, innerHeight);
            for (let i = 0; i < particlesArray.length; i++) {
                particlesArray[i].update();
            }
        }

        initParticles();
        animateParticles();

        window.addEventListener('resize', () => {
            canvas.width = innerWidth;
            canvas.height = innerHeight;
            initParticles();
        });
    }

    let currentStep = 1;
    let authMethod = 'phone';
    let qrLoginPoller = null;

    // --- Функции навигации по шагам ---
    function updateProgressBar() {
        progressSteps.removeClass('active');
        for (let i = 1; i <= currentStep; i++) {
            $(`.progress-step[data-step="${i}"]`).addClass('active');
        }
    }

    function showStep(step) {
        steps.removeClass('active');
        $(`#step-${step}`).addClass('active');
        currentStep = step;
        updateProgressBar();
        updateNavButtons();
    }

    function updateNavButtons() {
        backBtn.toggle(currentStep > 1 && currentStep < 4);
        nextBtn.toggle(currentStep === 3);
        startBtn.toggle(currentStep === 1);
    }

    function nextStep() {
        if (currentStep < 4) {
            if (currentStep === 3) {
                if (authMethod === 'phone') handlePhoneAuth();
                else finishLogin();
            } else {
                showStep(currentStep + 1);
            }
        }
    }

    function prevStep() {
        if (currentStep > 1) {
            showStep(currentStep - 1);
            if (currentStep === 2) clearInterval(qrLoginPoller);
        }
    }

    // --- Обработчики событий кнопок ---
    startBtn.on('click', () => showStep(tg_done ? 2 : (skip_creds ? 2 : 1)));
    nextBtn.on('click', nextStep);
    backBtn.on('click', prevStep);

    authPhoneBtn.on('click', () => {
        authMethod = 'phone';
        phoneAuthContent.show();
        qrAuthContent.hide();
        showStep(3);
    });

    authQrBtn.on('click', () => {
        authMethod = 'qr';
        qrAuthContent.show();
        phoneAuthContent.hide();
        initQrLogin();
        showStep(3);
    });

    addAccountBtn.on('click', () => location.reload());

    // --- Логика аутентификации ---
    function handlePhoneAuth() {
        const phone = phoneInput.val();
        const code = codeInput.val();
        const password = passwordInput.val();
        if ($('#block_phone').is(':visible') && phone) sendCodeRequest(phone);
        else if ($('#block_code').is(':visible') && code) sendTgCode(phone, code, password);
    }

    function sendCodeRequest(phone) {
        $.ajax({
            url: "/send_tg_code", type: "POST", data: phone,
            success: () => { $('#block_phone').hide(); $('#block_code').show(); },
            error: (xhr) => {
                if (xhr.status === 401) {
                    $('#block_phone').hide();
                    $('#block_code').show();
                    $('#block_2fa').show();
                } else {
                    Swal.fire('Ошибка', xhr.responseText || "Не удалось отправить код", 'error');
                }
            }
        });
    }

    function sendTgCode(phone, code, password) {
        $.ajax({
            url: "/tg_code",
            type: "POST",
            data: code + "\n" + phone + (password ? "\n" + password : ""),
            success: () => finishLogin(),
            error: (xhr) => {
                if (xhr.status === 401) {
                    $('#block_2fa').show();
                    Swal.fire('Требуется 2FA', 'Введите пароль двухфакторной аутентификации.', 'info');
                } else {
                    Swal.fire('Ошибка', xhr.responseText || "Неверный код или пароль", 'error');
                }
            }
        });
    }

    const qrCode = new QRCodeStyling({
        width: 256, height: 256, type: 'svg', image: '/static/favicon.png',
        dotsOptions: { color: '#8774e1', type: 'rounded' },
        backgroundOptions: { color: 'rgba(40, 40, 45, 0.8)' },
        imageOptions: { crossOrigin: 'anonymous', margin: 5 }
    });

    function initQrLogin() {
        $.post("/init_qr_login", (url) => {
            qrCode.update({ data: url });
            const qrContainer = document.querySelector('.qr_inner');
            if (qrContainer) {
                qrContainer.innerHTML = ''; // Очищаем контейнер перед добавлением нового QR
                qrCode.append(qrContainer);
            }
            startQrPolling();
        }).fail((xhr) => Swal.fire('Ошибка', xhr.responseText || "Не удалось инициализировать QR-логин", 'error'));
    }

    function startQrPolling() {
        clearInterval(qrLoginPoller); // Очищаем старый поллер на всякий случай
        qrLoginPoller = setInterval(() => {
            $.post("/get_qr_url", (newUrl) => {
                if (qrCode._options.data !== newUrl) qrCode.update({ data: newUrl });
            }).fail((xhr) => {
                clearInterval(qrLoginPoller);
                if (xhr.status === 200) finishLogin();
                else if (xhr.status === 403) promptFor2FA_QR();
                else Swal.fire('Ошибка', xhr.responseText || "Ошибка проверки QR-кода", 'error');
            });
        }, 2000);
    }

    function promptFor2FA_QR() {
        Swal.fire({
            title: 'Введите пароль 2FA', input: 'password', inputPlaceholder: 'Ваш пароль',
            showCancelButton: true, confirmButtonText: 'Войти', showLoaderOnConfirm: true,
            preConfirm: (password) => {
                return $.post("/qr_2fa", password).catch(error => {
                    Swal.showValidationMessage(`Ошибка: ${error.responseText}`);
                });
            },
            allowOutsideClick: () => !Swal.isLoading()
        }).then((result) => {
            if (result.isConfirmed) finishLogin();
        });
    }

    function finishLogin() {
        clearInterval(qrLoginPoller);
        $.post("/finish_login", () => {
            lottie.loadAnimation({
                container: installationIcon, renderer: 'svg', loop: false,
                autoplay: true, path: '/static/success.json'
            });
            showStep(4);
        });
    }

    updateNavButtons();
});