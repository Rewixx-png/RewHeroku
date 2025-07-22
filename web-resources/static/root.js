/*
  ©️ Dan Gazizullin, 2021-2023
  This file is a part of Hikka Userbot
  🌐 https://github.com/hikariatama/Hikka
  You can redistribute it and/or modify it under the terms of the GNU AGPLv3
  🔑 https://www.gnu.org/licenses/agpl-3.0.html
*/

$(document).ready(function() {
    let currentStep = 1;

    function goToStep(step) {
        $(".wizard-step").removeClass("active");
        $("#step-" + step).addClass("active");
        $(".progress-step").removeClass("active");
        $(`.progress-step[data-step="${step}"]`).addClass("active");
        currentStep = step;
        updateNavButtons();
    }

    function updateNavButtons() {
        if (currentStep > 1 && currentStep < 4) {
            $("#back-btn").show();
        } else {
            $("#back-btn").hide();
        }

        if (currentStep > 1 && currentStep < 3) {
            $("#next-btn").show();
        } else {
            $("#next-btn").hide();
        }
    }
    
    // Новая функция для сброса визарда
    function resetAndShowWizard() {
        // Сбросить все шаги и прогресс
        $(".wizard-step").removeClass("active");
        $(".progress-step").removeClass("active");

        // Показать первый шаг
        $("#step-1").addClass("active");
        $(".progress-step[data-step='1']").addClass("active");
        currentStep = 1;
        
        // Скрыть кнопки навигации, так как мы на первом шаге
        $("#back-btn, #next-btn").hide();
        
        // Показать кнопку "Начать настройку"
        $("#start-btn").show();
    }

    if (tg_done) {
        // Если установка уже завершена, сразу показываем финальный шаг
        goToStep(4);
        lottie.loadAnimation({
            container: document.getElementById('installation_icon'),
            renderer: 'svg',
            loop: false,
            autoplay: true,
            path: '/static/success.json'
        });
    }

    $("#start-btn").on("click", function() {
        goToStep(2);
    });

    $("#auth-phone-btn").on("click", function() {
        goToStep(3);
        $("#qr-auth-content").hide();
        $("#phone-auth-content").show();
        $("#next-btn").show(); // Показываем кнопку "Далее" для телефона
    });

    $("#auth-qr-btn").on("click", function() {
        goToStep(3);
        $("#phone-auth-content").hide();
        $("#qr-auth-content").show();
        $("#next-btn").hide(); // QR-код не требует кнопки "Далее"
        init_qr_login();
    });
    
    // Обработчик для новой кнопки
    $("#add-account-btn").on("click", function() {
        resetAndShowWizard();
    });

    $("#back-btn").on("click", function() {
        if (currentStep > 1) {
            goToStep(currentStep - 1);
        }
    });

    $("#next-btn").on("click", function() {
        if (currentStep < 4) {
             if(currentStep == 3 && $("#phone-auth-content").is(":visible")) {
                send_tg_code();
             } else {
                goToStep(currentStep + 1);
             }
        }
    });

    $('#phone').keypress(function (e) {
        if (e.which == 13) {
            send_tg_code();
            return false;
        }
    });

    $('#code').keypress(function (e) {
        if (e.which == 13) {
            tg_code();
            return false;
        }
    });

    $('#password').keypress(function (e) {
        if (e.which == 13) {
            tg_code();
            return false;
        }
    });

    function send_tg_code() {
        var phone = $("#phone").val();
        $.post( "/send_tg_code", phone, function( data ) {
            if (data == "ok") {
                $("#block_phone").fadeOut(200, function() {
                    $("#block_code").fadeIn(200);
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: data
                })
            }
        });
    }

    function tg_code() {
        var phone = $("#phone").val();
        var code = $("#code").val();
        var password = $("#password").val();
        var data = code + "\n" + phone + "\n" + password;
        $.post("/tg_code", data, function( data ) {
            if (data == "SUCCESS") {
                finish_login();
            }
        }).fail(function(data) {
            if(data.status == 401) {
                $("#block_code").fadeOut(200, function() {
                    $("#block_2fa").fadeIn(200);
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: data.responseText,
                })
            }
        })
    }
    
    function finish_login() {
        $.post("/finish_login", function( data ) {
            goToStep(4);
            lottie.loadAnimation({
                container: document.getElementById('installation_icon'),
                renderer: 'svg',
                loop: false,
                autoplay: true,
                path: '/static/success.json'
            });
        });
    }

    const qrCode = new QRCodeStyling({
        width: 256,
        height: 256,
        type: "svg",
        data: "https://heroku.com",
        image: "/static/icon.png",
        dotsOptions: {
            color: "#8774e1",
            type: "rounded"
        },
        backgroundOptions: {
            color: "rgba(255, 255, 255, 0.9)",
        },
        imageOptions: {
            crossOrigin: "anonymous",
            margin: 5
        }
    });

    function init_qr_login() {
        qrCode.append(document.querySelector("#qr-auth-content .qr_inner"));
        $.post("/init_qr_login", function (url) {
            qrCode.update({ data: url });
            check_qr_status();
        });
    }
    
    function check_qr_status() {
        $.post("/get_qr_url", function(url) {
            qrCode.update({ data: url });
            setTimeout(check_qr_status, 1000);
        }).fail(function(r) {
            if (r.status == 200) {
                finish_login();
            } else if (r.status == 403) {
                Swal.fire({
                    title: 'Двухфакторная аутентификация',
                    input: 'text',
                    inputAttributes: {
                        autocapitalize: 'off'
                    },
                    showCancelButton: false,
                    confirmButtonText: 'Войти',
                    showLoaderOnConfirm: true,
                    preConfirm: (password) => {
                        return $.post("/qr_2fa", password).then(response => {
                            if (response != "SUCCESS") {
                                throw new Error(response.responseText)
                            }

                            return response.data
                        }).catch(error => {
                            Swal.showValidationMessage(
                                `Request failed: ${error}`
                            )
                        })
                    },
                    allowOutsideClick: false,
                }).then((result) => {
                    if (result.isConfirmed) {
                        finish_login();
                    }
                })
            } else {
                setTimeout(check_qr_status, 1000);
            }
        });
    }
});