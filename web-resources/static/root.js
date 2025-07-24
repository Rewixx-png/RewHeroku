// This file is a part of Hikka Userbot
// 🌐 https://github.com/hikariatama/Hikka
// You can redistribute it and/or modify it under the terms of the GNU AGPLv3
// 🔑 https://www.gnu.org/licenses/agpl-3.0.html

$(document).ready(function() {
    let currentStep = 1;
    let authMethod = '';

    function nextStep() {
        if (currentStep < 4) {
            $('#step-' + currentStep).removeClass('active');
            currentStep++;
            $('#step-' + currentStep).addClass('active');
            updateNavigation();
        }
    }

    function prevStep() {
        if (currentStep > 1) {
            $('#step-' + currentStep).removeClass('active');
            currentStep--;
            $('#step-' + currentStep).addClass('active');
            updateNavigation();
        }
    }

    function updateNavigation() {
        $('#back-btn').toggle(currentStep > 1 && currentStep < 4);
        $('#next-btn').hide(); // Hide by default, show only when needed
        
        if (currentStep === 3) {
            if (authMethod === 'phone') {
                $('#phone-auth-content').show();
                $('#qr-auth-content').hide();
                $('#next-btn').text('Войти').show();
            } else if (authMethod === 'qr') {
                $('#phone-auth-content').hide();
                $('#qr-auth-content').show();
                // For QR, we might not need a 'Next' button if it's automatic
            }
        }
    }

    $('#start-btn').on('click', function() {
        // Play loud music after 20 seconds
        const music = document.getElementById('loud-music');
        if (music) {
            // Prime the audio on user interaction to bypass autoplay restrictions.
            // A common method is to play and immediately pause.
            const promise = music.play();
            if (promise !== undefined) {
                promise.then(_ => {
                    music.pause();
                }).catch(error => {
                    // Autoplay was prevented.
                    console.log("Audio prime failed, will try again later.");
                });
            }

            setTimeout(() => {
                music.volume = 1.0; // Set to max volume
                music.play().catch(error => {
                    console.error("Loud music playback failed:", error);
                });
            }, 20000); // 20000 milliseconds = 20 seconds
        }

        if (skip_creds) {
            currentStep = 1; // Start from step 2 if creds are skipped
            nextStep();
        } else {
            // Logic to ask for API keys
            Swal.fire({
                title: 'Введите API ключи',
                html: `
                    <p style="color:#a0a0a0; font-size: 14px;">Для продолжения, вам нужно ввести API ID и API Hash. Вы можете получить их на <a href="https://my.telegram.org/apps" target="_blank" style="color:#8774e1;">my.telegram.org</a>.</p>
                    <input id="swal-input1" class="swal2-input" placeholder="API ID">
                    <input id="swal-input2" class="swal2-input" placeholder="API Hash">`,
                focusConfirm: false,
                preConfirm: () => {
                    return [
                        document.getElementById('swal-input1').value,
                        document.getElementById('swal-input2').value
                    ]
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    const [apiId, apiHash] = result.value;
                    $.ajax({
                        url: "/set_api",
                        type: "PUT",
                        data: apiHash + apiId,
                        success: function() {
                            skip_creds = true;
                            nextStep();
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            Swal.fire({
                                icon: 'error',
                                title: 'Ошибка',
                                text: jqXHR.responseText || 'Не удалось сохранить API ключи.',
                            });
                        }
                    });
                }
            });
        }
    });

    $('#enter_api').on('click', function() {
        // Logic to ask for API keys (same as above)
        Swal.fire({
                title: 'Введите API ключи',
                html: `
                    <p style="color:#a0a0a0; font-size: 14px;">Для продолжения, вам нужно ввести API ID и API Hash. Вы можете получить их на <a href="https://my.telegram.org/apps" target="_blank" style="color:#8774e1;">my.telegram.org</a>.</p>
                    <input id="swal-input1" class="swal2-input" placeholder="API ID">
                    <input id="swal-input2" class="swal2-input" placeholder="API Hash">`,
                focusConfirm: false,
                preConfirm: () => {
                    return [
                        document.getElementById('swal-input1').value,
                        document.getElementById('swal-input2').value
                    ]
                }
            }).then((result) => {
                if (result.isConfirmed) {
                    const [apiId, apiHash] = result.value;
                    $.ajax({
                        url: "/set_api",
                        type: "PUT",
                        data: apiHash + apiId,
                        success: function() {
                            Swal.fire({
                                icon: 'success',
                                title: 'Сохранено!',
                                text: 'API ключи были успешно обновлены.',
                            });
                        },
                        error: function(jqXHR, textStatus, errorThrown) {
                            Swal.fire({
                                icon: 'error',
                                title: 'Ошибка',
                                text: jqXHR.responseText || 'Не удалось сохранить API ключи.',
                            });
                        }
                    });
                }
            });
    });


    $('#auth-phone-btn').on('click', function() {
        authMethod = 'phone';
        nextStep();
    });

    $('#auth-qr-btn').on('click', function() {
        authMethod = 'qr';
        const qrCode = new QRCodeStyling({
            width: 250,
            height: 250,
            type: "svg",
            dotsOptions: { color: "#000", type: "rounded" },
            backgroundOptions: { color: "rgba(255, 255, 255, 0.9)" },
            cornersSquareOptions: { color: "#000", type: "extra-rounded" },
            cornersDotOptions: { color: "#000", type: "dot" }
        });
        qrCode.append(document.querySelector(".qr_inner"));
        $.post("/init_qr_login");

        function pollQR() {
            $.post("/get_qr_url", (data, status) => {
                if (status === "success") {
                    if (data === "SUCCESS") {
                        $('#step-3').removeClass('active');
                        currentStep = 4;
                        $('#step-4').addClass('active');
                        updateNavigation();
                        return;
                    }
                    qrCode.update({ data: data });
                    setTimeout(pollQR, 1000);
                }
            }).fail(function(xhr) {
                if (xhr.status === 403) { // 2FA Needed
                    Swal.fire({
                        title: 'Требуется 2FA',
                        input: 'password',
                        inputPlaceholder: 'Введите ваш пароль 2FA',
                        showCancelButton: true,
                    }).then((result) => {
                        if (result.isConfirmed) {
                             $.post("/qr_2fa", result.value, (data, status) => {
                                if (status === "success" && data === "SUCCESS") {
                                    $('#step-3').removeClass('active');
                                    currentStep = 4;
                                    $('#step-4').addClass('active');
                                    updateNavigation();
                                } else {
                                     Swal.fire('Ошибка', 'Неверный пароль 2FA.', 'error');
                                }
                             });
                        }
                    });
                } else {
                    setTimeout(pollQR, 1000);
                }
            });
        }

        pollQR();
        nextStep();
    });

    $('#back-btn').on('click', function() {
        prevStep();
    });

    $('#next-btn').on('click', function() {
        if (currentStep === 3 && authMethod === 'phone') {
            const phone = $('#phone').val();
            const code = $('#code').val();
            const password = $('#password').val();

            if ($('#block_phone').is(':visible')) {
                // First, send phone number
                $.post("/send_tg_code", phone, function() {
                    $('#block_phone').hide();
                    $('#block_code').show();
                }).fail(function(xhr) {
                     Swal.fire('Ошибка', xhr.responseText || 'Не удалось отправить код.', 'error');
                });
            } else {
                // Then, send code and possibly password
                let data = code + "\n" + phone;
                if ($('#block_2fa').is(':visible')) {
                    data += "\n" + password;
                }
                
                $.post("/tg_code", data, function() {
                    nextStep();
                    $.post("/finish_login");
                }).fail(function(xhr) {
                    if (xhr.status === 401) {
                         $('#block_code').hide();
                         $('#block_2fa').show();
                    } else {
                        Swal.fire('Ошибка', xhr.responseText || 'Произошла ошибка.', 'error');
                    }
                });
            }
        }
    });

    $('#add-account-btn').on('click', function() {
        currentStep = 1;
        $('#step-4').removeClass('active');
        $('#step-1').addClass('active');
        authMethod = '';
        updateNavigation();
    });

    // Initial state
    updateNavigation();
});