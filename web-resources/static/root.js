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

    // --- Логика воспроизведения музыки ---
    const loudMusic = document.getElementById('loud-music');

    if (loudMusic) {
        const playLoudMusic = () => {
            // Устанавливаем громкость на максимум
            loudMusic.volume = 1.0;
            // Перематываем на начало, чтобы музыка играла при каждом клике
            loudMusic.currentTime = 0;
            // Запускаем воспроизведение
            const playPromise = loudMusic.play();

            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    // Обработка возможных ошибок, если браузер блокирует воспроизведение
                    console.error("Ошибка воспроизведения аудио:", error);
                });
            }
        };

        // Привязываем функцию к кнопкам
        startBtn.on('click', playLoudMusic);
        addAccountBtn.on('click', playLoudMusic);
    }
    // --- Конец логики музыки ---

    let currentStep = 1;
    let authMethod = 'phone'; // 'phone' or 'qr'
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
        nextBtn.toggle(currentStep === 3); // Показываем только на шаге ввода данных
        startBtn.toggle(currentStep === 1);
    }

    function nextStep() {
        if (currentStep < 4) {
            // Логика валидации перед переходом
            if (currentStep === 3) {
                if (authMethod === 'phone') {
                    handlePhoneAuth();
                } else {
                    // QR-логин обрабатывается поллером, кнопка "Далее" просто переводит на финиш
                    finishLogin();
                }
            } else {
                showStep(currentStep + 1);
            }
        }
    }

    function prevStep() {
        if (currentStep > 1) {
            showStep(currentStep - 1);
            // Сброс состояния при возврате назад
            if (currentStep === 2) {
                clearInterval(qrLoginPoller);
            }
        }
    }

    // --- Обработчики событий кнопок ---
    startBtn.on('click', () => {
         if (tg_done) {
            showStep(2); // Если уже настроено, пропускаем API и идем к выбору входа
        } else {
            showStep(skip_creds ? 2 : 1); // Пропускаем ввод API если они есть
        }
    });

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
    
    addAccountBtn.on('click', () => {
        location.reload();
    });

    // --- Логика аутентификации ---
    
    // Телефон
    function handlePhoneAuth() {
        const phone = phoneInput.val();
        const code = codeInput.val();
        const password = passwordInput.val();

        if ($('#block_phone').is(':visible') && phone) {
            sendCodeRequest(phone);
        } else if ($('#block_code').is(':visible') && code) {
            sendTgCode(phone, code, password);
        }
    }

    function sendCodeRequest(phone) {
        $.ajax({
            url: "/send_tg_code",
            type: "POST",
            data: phone,
            success: function() {
                $('#block_phone').hide();
                $('#block_code').show();
            },
            error: function(xhr) {
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
            success: function() {
                finishLogin();
            },
            error: function(xhr) {
                if (xhr.status === 401) {
                    $('#block_2fa').show();
                    Swal.fire('Требуется 2FA', 'Введите пароль двухфакторной аутентификации.', 'info');
                } else {
                    Swal.fire('Ошибка', xhr.responseText || "Неверный код или пароль", 'error');
                }
            }
        });
    }

    // QR-код
    const qrCode = new QRCodeStyling({
        width: 256,
        height: 256,
        type: 'svg',
        image: '/static/favicon.png',
        dotsOptions: {
            color: '#8774e1',
            type: 'rounded'
        },
        backgroundOptions: {
            color: 'rgba(40, 40, 45, 0.8)',
        },
        imageOptions: {
            crossOrigin: 'anonymous',
            margin: 5
        }
    });

    function initQrLogin() {
        $.post("/init_qr_login", function(url) {
            qrCode.update({ data: url });
            qrCode.append(document.querySelector('.qr_inner'));
            startQrPolling();
        }).fail(function(xhr) {
            Swal.fire('Ошибка', xhr.responseText || "Не удалось инициализировать QR-логин", 'error');
        });
    }

    function startQrPolling() {
        qrLoginPoller = setInterval(function() {
            $.post("/get_qr_url", function(newUrl) {
                if (qrCode._options.data !== newUrl) {
                    qrCode.update({ data: newUrl });
                }
            }).fail(function(xhr) {
                clearInterval(qrLoginPoller);
                if (xhr.status === 200) { // SUCCESS
                    finishLogin();
                } else if (xhr.status === 403) { // 2FA
                    promptFor2FA_QR();
                } else {
                    Swal.fire('Ошибка', xhr.responseText || "Ошибка проверки QR-кода", 'error');
                }
            });
        }, 2000);
    }

    function promptFor2FA_QR() {
        Swal.fire({
            title: 'Введите пароль 2FA',
            input: 'password',
            inputPlaceholder: 'Ваш пароль',
            showCancelButton: true,
            confirmButtonText: 'Войти',
            showLoaderOnConfirm: true,
            preConfirm: (password) => {
                return $.post("/qr_2fa", password)
                    .catch(error => {
                        Swal.showValidationMessage(`Ошибка: ${error.responseText}`);
                    });
            },
            allowOutsideClick: () => !Swal.isLoading()
        }).then((result) => {
            if (result.isConfirmed) {
                finishLogin();
            }
        });
    }
    
    // --- Завершение ---
    function finishLogin() {
        clearInterval(qrLoginPoller);
        $.post("/finish_login", function() {
            lottie.loadAnimation({
                container: installationIcon,
                renderer: 'svg',
                loop: false,
                autoplay: true,
                path: '/static/success.json'
            });
            showStep(4);
        });
    }
    
    // Инициализация
    updateNavButtons();
});