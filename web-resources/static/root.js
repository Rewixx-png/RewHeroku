$(document).ready(function () {
    let currentStep = 1;
    let loginState = 'phone'; // Состояния: 'phone', 'code', '2fa', 'qr', 'finished'
    let phone_number = '';
    let qr_poller = null; // Для интервала опроса QR-кода

    const steps = $(".wizard-step");
    const progressSteps = $(".progress-step");

    function updateWizard() {
        steps.removeClass("active");
        $("#step-" + currentStep).addClass("active");

        progressSteps.removeClass("active");
        progressSteps.each(function () {
            if ($(this).data("step") <= currentStep) {
                $(this).addClass("active");
            }
        });

        // Кнопка "Назад" видна на шагах 2 и 3
        $("#back-btn").toggle(currentStep > 1 && currentStep < 4);
        // Кнопка "Далее" видна только на шаге 3 (ввод данных)
        $("#next-btn").toggle(currentStep === 3);
    }

    // Функция для полного сброса состояния мастера установки
    function resetWizardState() {
        currentStep = 2;
        loginState = 'phone';
        phone_number = '';
        if (qr_poller) {
            clearInterval(qr_poller);
            qr_poller = null;
        }
        $('#phone').val('');
        $('#code').val('');
        $('#password').val('');
        $("#block_phone").show();
        $("#block_code").hide();
        $("#block_2fa").hide();
        $("#phone-auth-content").show();
        $("#qr-auth-content").hide();
        $("#step-4").removeClass("active"); // Скрываем финальный шаг
        updateWizard();
    }
    
    // Функция для запроса авторизации перед добавлением нового аккаунта
    async function authorizeAndProceed() {
        Swal.fire({
            title: 'Подтверждение',
            text: 'Пожалуйста, подтвердите действие в вашем основном аккаунте Telegram. Мы отправили туда сообщение.',
            icon: 'info',
            allowOutsideClick: false,
            showConfirmButton: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        try {
            const response = await fetch('/web_auth', { method: 'POST' });
            const session_key = await response.text();

            if (response.ok && session_key.startsWith("heroku_")) {
                $.cookie("session", session_key, { expires: 1, path: '/' });
                Swal.close();
                resetWizardState(); // Сбрасываем и переходим к шагу 2
            } else {
                let errorText = "Авторизация не удалась. Возможно, время ожидания истекло.";
                if (session_key === "TIMEOUT") {
                    errorText = "Время ожидания подтверждения истекло. Попробуйте снова.";
                } else if (session_key === "CONFIRMATION_FAILED") {
                    errorText = "Не удалось отправить запрос на подтверждение.";
                }
                Swal.fire('Ошибка', errorText, 'error');
            }
        } catch (e) {
            Swal.fire('Ошибка', 'Не удалось связаться с сервером для авторизации.', 'error');
        }
    }
    
    // Назначаем обработчик на кнопку добавления аккаунта
    $("#add-account-btn").click(authorizeAndProceed);

    // Начало работы мастера
    $("#start-btn").click(function () {
        currentStep = 2;
        updateWizard();
    });

    // Выбор метода входа
    $("#auth-phone-btn").click(function () {
        currentStep = 3;
        $("#phone-auth-content").show();
        $("#qr-auth-content").hide();
        loginState = 'phone';
        updateWizard();
    });

    $("#auth-qr-btn").click(function () {
        currentStep = 3;
        $("#phone-auth-content").hide();
        $("#qr-auth-content").show();
        loginState = 'qr';
        updateWizard();
        init_qr_login();
    });

    // Кнопка "Назад"
    $("#back-btn").click(function () {
        if (currentStep > 1) {
            currentStep--;
            // При возврате сбрасываем состояние, чтобы избежать зацикливания
            loginState = 'phone';
            phone_number = '';
            if (qr_poller) clearInterval(qr_poller);
            $("#block_phone").show();
            $("#block_code").hide();
            $("#block_2fa").hide();
            updateWizard();
        }
    });

    // Кнопка "Далее" (основная логика входа)
    $("#next-btn").click(async function () {
        $(this).prop('disabled', true); // Блокируем кнопку на время запроса

        if (loginState === 'phone') {
            phone_number = $('#phone').val();
            if (!phone_number) {
                Swal.fire('Oops...', 'Введите номер телефона', 'error');
                $(this).prop('disabled', false);
                return;
            }
            try {
                const response = await fetch('/send_tg_code', { method: 'POST', body: phone_number });
                if (response.ok) {
                    loginState = 'code';
                    $("#block_phone").hide();
                    $("#block_code").show();
                } else {
                    const errorText = await response.text();
                    Swal.fire('Oops...', errorText || 'Ошибка отправки кода', 'error');
                }
            } catch (e) { Swal.fire('Oops...', 'Ошибка сети', 'error'); }
        } else if (loginState === 'code') {
            const code = $('#code').val();
            if (!code) {
                Swal.fire('Oops...', 'Введите код подтверждения', 'error');
                $(this).prop('disabled', false);
                return;
            }
            try {
                const response = await fetch('/tg_code', { method: 'POST', body: code + '\n' + phone_number });
                if (response.ok) {
                    loginState = 'finished';
                    await fetch('/finish_login', { method: 'POST' });
                    currentStep = 4;
                    updateWizard();
                    lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: false,
                        autoplay: true,
                        path: '/static/success.json'
                    });
                } else if (response.status === 401) {
                    loginState = '2fa';
                    $("#block_code").hide();
                    $("#block_2fa").show();
                } else {
                    const errorText = await response.text();
                    Swal.fire('Oops...', errorText || 'Неверный код', 'error');
                }
            } catch (e) { Swal.fire('Oops...', 'Ошибка сети', 'error'); }
        } else if (loginState === '2fa') {
            const password = $('#password').val();
            if (!password) {
                Swal.fire('Oops...', 'Введите пароль 2FA', 'error');
                $(this).prop('disabled', false);
                return;
            }
            try {
                const response = await fetch('/tg_code', { method: 'POST', body: $('#code').val() + '\n' + phone_number + '\n' + password });
                if (response.ok) {
                    loginState = 'finished';
                    await fetch('/finish_login', { method: 'POST' });
                    currentStep = 4;
                    updateWizard();
                    lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: false,
                        autoplay: true,
                        path: '/static/success.json'
                    });
                } else {
                    const errorText = await response.text();
                    Swal.fire('Oops...', errorText || 'Неверный пароль', 'error');
                }
            } catch (e) { Swal.fire('Oops...', 'Ошибка сети', 'error'); }
        }
        $(this).prop('disabled', false);
    });

    // Первоначальная настройка страницы
    if (tg_done) {
        currentStep = 4;
        updateWizard();
        $("#installation_icon").hide();
        $(".title").text("RewHeroku");
        $(".description").html("Вы можете добавить еще один аккаунт или закрыть эту страницу.");
    }

    // Логика для QR-кода
    async function init_qr_login() {
        const qrCode = new QRCodeStyling({
            width: 256,
            height: 256,
            type: "svg",
            dotsOptions: { color: "#000", type: "rounded" },
            backgroundOptions: { color: "#FFF" },
            cornersSquareOptions: { type: "extra-rounded" },
            cornersDotOptions: { type: "" }
        });
        
        try {
            const response = await fetch('/init_qr_login', { method: 'POST' });
            const url = await response.text();
            qrCode.update({ data: url });
            qrCode.append(document.querySelector(".qr_inner"));

            qr_poller = setInterval(async () => {
                const qr_response = await fetch('/get_qr_url', { method: 'POST' });
                if (qr_response.status === 200) {
                    clearInterval(qr_poller);
                    loginState = 'finished';
                    await fetch('/finish_login', { method: 'POST' });
                    currentStep = 4;
                    updateWizard();
                     lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: false,
                        autoplay: true,
                        path: '/static/success.json'
                    });
                } else if (qr_response.status === 403) { // 2FA
                    clearInterval(qr_poller);
                    loginState = '2fa_qr';
                    // Тут можно показать поле для ввода 2FA пароля, если нужно
                    Swal.fire({
                        title: 'Введите пароль 2FA',
                        input: 'password',
                        inputAttributes: { autocapitalize: 'off' },
                        showCancelButton: true,
                        confirmButtonText: 'Войти',
                        showLoaderOnConfirm: true,
                        preConfirm: async (password) => {
                            try {
                                const fa_response = await fetch('/qr_2fa', { method: 'POST', body: password });
                                if (!fa_response.ok) {
                                    throw new Error(await fa_response.text());
                                }
                                return fa_response.text();
                            } catch (error) {
                                Swal.showValidationMessage(`Запрос не удался: ${error}`);
                            }
                        },
                        allowOutsideClick: () => !Swal.isLoading()
                    }).then(async (result) => {
                        if (result.isConfirmed) {
                             loginState = 'finished';
                             await fetch('/finish_login', { method: 'POST' });
                             currentStep = 4;
                             updateWizard();
                             lottie.loadAnimation({
                                container: document.getElementById('installation_icon'),
                                renderer: 'svg',
                                loop: false,
                                autoplay: true,
                                path: '/static/success.json'
                            });
                        }
                    });
                } else {
                    const new_url = await qr_response.text();
                    qrCode.update({ data: new_url });
                }
            }, 1000);
        } catch(e) {
            Swal.fire('Oops...', 'Не удалось инициализировать QR-вход.', 'error');
        }
    }
});