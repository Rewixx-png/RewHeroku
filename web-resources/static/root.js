$(document).ready(function () {
    let currentStep = 1;
    let loginState = 'phone'; // 'phone', 'code', '2fa'
    let phone_number = '';

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

        $("#back-btn").toggle(currentStep > 1 && currentStep < 4);
        $("#next-btn").toggle(currentStep > 1 && currentStep < 4);
    }

    $("#start-btn").click(function () {
        if (!skip_creds || tg_done) {
            currentStep = 2;
        } else {
            // Если API ключи уже есть и это не добавление нового акка, пропускаем
            currentStep = 2;
        }
        updateWizard();
    });

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
    
    $("#add-account-btn").click(function () {
        // Сброс состояния для добавления нового аккаунта
        currentStep = 2;
        loginState = 'phone';
        phone_number = '';
        $('#phone').val('');
        $('#code').val('');
        $('#password').val('');
        $("#block_phone").show();
        $("#block_code").hide();
        $("#block_2fa").hide();
        updateWizard();
    });


    $("#back-btn").click(function () {
        if (currentStep > 1) {
            // При возврате с шага ввода данных на шаг выбора метода
            if (currentStep === 3) {
                currentStep = 2;
                // Сбрасываем состояние, чтобы можно было начать заново
                loginState = 'phone';
                phone_number = '';
                $('#phone').val('');
                $('#code').val('');
                $('#password').val('');
                $("#block_phone").show();
                $("#block_code").hide();
                $("#block_2fa").hide();
            }
            updateWizard();
        }
    });

    $("#next-btn").click(async function () {
        $(this).prop('disabled', true); // Блокируем кнопку на время запроса

        if (currentStep === 3) {
            if (loginState === 'phone') {
                phone_number = $('#phone').val();
                if (!phone_number) {
                    Swal.fire('Oops...', 'Введите номер телефона', 'error');
                    $(this).prop('disabled', false);
                    return;
                }
                
                try {
                    const response = await fetch('/send_tg_code', {
                        method: 'POST',
                        body: phone_number
                    });

                    if (response.ok) {
                        loginState = 'code';
                        $("#block_phone").hide();
                        $("#block_code").show();
                        $("#block_2fa").hide();
                    } else {
                        const errorText = await response.text();
                        Swal.fire('Oops...', errorText || 'Ошибка отправки кода', 'error');
                    }
                } catch (e) {
                    Swal.fire('Oops...', 'Ошибка сети', 'error');
                }

            } else if (loginState === 'code') {
                const code = $('#code').val();
                if (!code) {
                    Swal.fire('Oops...', 'Введите код подтверждения', 'error');
                    $(this).prop('disabled', false);
                    return;
                }
                
                try {
                    const response = await fetch('/tg_code', {
                        method: 'POST',
                        body: code + '\n' + phone_number
                    });
                    
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
                        $("#block_phone").hide();
                        $("#block_code").hide();
                        $("#block_2fa").show();
                    } else {
                        const errorText = await response.text();
                        Swal.fire('Oops...', errorText || 'Неверный код', 'error');
                    }
                } catch(e) {
                    Swal.fire('Oops...', 'Ошибка сети', 'error');
                }

            } else if (loginState === '2fa') {
                const password = $('#password').val();
                if (!password) {
                    Swal.fire('Oops...', 'Введите пароль 2FA', 'error');
                    $(this).prop('disabled', false);
                    return;
                }

                try {
                    const response = await fetch('/tg_code', {
                        method: 'POST',
                        body: $('#code').val() + '\n' + phone_number + '\n' + password
                    });

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
                } catch(e) {
                     Swal.fire('Oops...', 'Ошибка сети', 'error');
                }
            }
        }
        $(this).prop('disabled', false); // Разблокируем кнопку
    });
    
    // Initial setup if adding account from existing session
    if (tg_done) {
        currentStep = 4;
        updateWizard();
        $("#installation_icon").hide();
        $(".title").text("RewHeroku");
        $(".description").html("Вы можете добавить еще один аккаунт или закрыть эту страницу.");
    }
});