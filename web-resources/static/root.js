var api_id = "";
var api_hash = "";
var phone = "";
var code = "";
var password = "";
var session = $.cookie("session");
// <<< НАЧАЛО ИЗМЕНЕНИЙ: Переменная для временной сессии с PIN-кодом >>>
var pin_session_id = "";
// <<< КОНЕЦ ИЗМЕНЕНИЙ >>>

if (skip_creds) {
    $(".description").hide();
    $("#block_phone, #block_custom_bot").css("display", "block");
    $("#continue_btn, #denyqr").css("display", "flex");
}

// <<< НАЧАЛО ИЗМЕНЕНИЙ: Новая логика авторизации через PIN >>>
function requestPin() {
    $(".main").fadeOut(200);
    $(".pin-code-form").fadeIn(200);
    lottie.loadAnimation({
        container: document.getElementById('tg_icon'),
        renderer: 'svg',
        loop: true,
        autoplay: true,
        path: 'https://static.dan.tatar/telegram.json'
    });
    fetch("/request_pin", {
            method: "POST",
            credentials: "include"
        })
        .then(response => response.json())
        .then((data) => {
            if (data.session_id) {
                pin_session_id = data.session_id;
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'PIN Request Failed',
                    text: data.message || "Could not request a PIN code.",
                });
                $(".pin-code-form").fadeOut(200);
                $(".main").fadeIn(200);
            }
        });
}

$("#verify_pin_btn").on("click", function() {
    let pin = $(".pin-input").val();
    if (pin.length !== 6) {
        Swal.fire({
            icon: 'warning',
            title: 'Invalid PIN',
            text: 'Please enter the 6-digit PIN code you received in Telegram.',
        });
        return;
    }

    fetch("/verify_pin", {
            method: "POST",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pin: pin,
                session_id: pin_session_id
            }),
            credentials: "include"
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            } else {
                return response.text().then(text => {
                    throw new Error(text)
                });
            }
        })
        .then((data) => {
            if (data.status === "ok") {
                // Прячем форму PIN и показываем основную форму входа
                $(".pin-code-form").fadeOut(200);
                $(".main").fadeIn(200);
                auth_required = false; // Мы авторизованы
                $(".description").hide();
                $("#block_qr_login, #denyqr").css("display", "block");
                $("#get_started, #add_another_account, #enter_api").hide();
                init_qr();
            }
        })
        .catch(error => {
            let errorMsg = "An unknown error occurred.";
            try {
                let jsonError = JSON.parse(error.message);
                errorMsg = jsonError.message || "Invalid PIN or session expired.";
            } catch (e) {
                errorMsg = error.message || "Invalid PIN or session expired.";
            }

            Swal.fire({
                icon: 'error',
                title: 'Authentication Failed',
                text: errorMsg,
            });
            $(".pin-input").val("");
        });
});

// Навешиваем обработчики на обе кнопки
$("#get_started, #add_another_account").on("click", function() {
    check_can_add();
    if (auth_required) {
        requestPin();
    } else {
        // Если уже авторизованы, сразу показываем форму
        $(".description, #get_started, #add_another_account").hide();
        $("#block_qr_login, #denyqr").css("display", "block");
        init_qr();
    }
});
// <<< КОНЕЦ ИЗМЕНЕНИЙ >>>


if (
    document.referrer.includes("https://my.telegram.org/") ||
    document.referrer.includes("https://my.telegram.org/apps")
) {
    $("#enter_api").trigger("click");
}

$(document).on("keyup", function(e) {
    if (e.key === "Enter") {
        if ($(".pin-code-form").is(":visible")) {
            $("#verify_pin_btn").trigger("click");
        } else if ($(".auth-code-form").is(":visible")) {
            $(".enter").trigger("click");
        }
    }
})

function check_can_add() {
    fetch("/can_add", {
            method: "POST",
            credentials: "include"
        })
        .then(response => response.status)
        .then((status) => {
            if (status != 200) {
                $(".main").fadeOut(200);
                $(".eula-form").fadeIn(200);
                lottie.loadAnimation({
                    container: document.getElementById('law'),
                    renderer: 'svg',
                    loop: true,
                    autoplay: true,
                    path: 'https://static.dan.tatar/law.json'
                });
            }
        })
}

$("#denyqr").on("click", function() {
    $("#block_qr_login, #denyqr").hide();
    $("#block_phone, #block_custom_bot").css("display", "block");
    $("#continue_btn").css("display", "flex");
})

$(".phone").on("input", function() {
    phone = $(".phone").val();
})

$(".custom_bot").on("input", function() {
    var custom_bot = $(".custom_bot").val();
    fetch("/custom_bot", {
            method: "POST",
            body: custom_bot,
            credentials: "include"
        })
        .then(response => response.text())
        .then((response) => {
            if (response == "OK") {
                $(".custom_bot").css("border", "1px solid #18cc18");
            } else {
                $(".custom_bot").css("border", "1px solid #c54245");
            }
        })
})

$(".code-input").on("input", function() {
    if ($(".code-input").attr("placeholder") == "•••••") {
        code = $(".code-input").val();
    } else {
        password = $(".code-input").val();
    }
})

$(".enter").on("click", function() {
    if ($(".code-input").attr("placeholder") == "•••••") {
        fetch("/tg_code", {
                method: "POST",
                body: code + "\n" + phone,
                credentials: "include"
            })
            .then(response => response.text())
            .then((text) => {
                if (text == "2FA Password required") {
                    $(".code-input").val("").attr("placeholder", "••••••••••••••••");
                    $(".code-caption").text("Enter your 2FA password")
                    $(".enter").addClass("tgcode")
                } else if (text == "SUCCESS") {
                    $(".auth-code-form").fadeOut(200);
                    $(".installation").fadeOut(200);
                    $(".finish_block").fadeIn(200);
                    lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: 'https://static.dan.tatar/finish.json'
                    });
                    fetch("/finish_login", {
                        method: "POST",
                        credentials: "include"
                    })
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: text,
                    })
                }
            })
    } else if ($(this).hasClass("tgcode")) {
        fetch("/tg_code", {
                method: "POST",
                body: code + "\n" + phone + "\n" + password,
                credentials: "include"
            })
            .then(response => response.text())
            .then((text) => {
                if (text == "SUCCESS") {
                    $(".auth-code-form").fadeOut(200);
                    $(".installation").fadeOut(200);
                    $(".finish_block").fadeIn(200);
                    lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: 'https://static.dan.tatar/finish.json'
                    });
                    fetch("/finish_login", {
                        method: "POST",
                        credentials: "include"
                    })
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: text,
                    })
                }
            })
    } else {
        fetch("/qr_2fa", {
                method: "POST",
                body: password,
                credentials: "include"
            })
            .then(response => response.text())
            .then((text) => {
                if (text == "SUCCESS") {
                    $(".auth-code-form").fadeOut(200);
                    $(".installation").fadeOut(200);
                    $(".finish_block").fadeIn(200);
                    lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: 'https://static.dan.tatar/finish.json'
                    });
                    fetch("/finish_login", {
                        method: "POST",
                        credentials: "include"
                    })
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Oops...',
                        text: text,
                    })
                }
            })
    }
})

$("#continue_btn").on("click", function() {
    fetch("/send_tg_code", {
            method: "POST",
            body: phone,
            credentials: "include"
        })
        .then(response => response.text())
        .then((text) => {
            if (text == "ok") {
                $(".main").fadeOut(200);
                $(".auth-code-form").fadeIn(200);
                $(".code-input").attr("placeholder", "•••••");
                lottie.loadAnimation({
                    container: document.getElementById('monkey'),
                    renderer: 'svg',
                    loop: true,
                    autoplay: true,
                    path: 'https://static.dan.tatar/monkey.json'
                });
                lottie.loadAnimation({
                    container: document.getElementById('monkey-close'),
                    renderer: 'svg',
                    loop: true,
                    autoplay: true,
                    path: 'https://static.dan.tatar/monkey_close.json'
                });
            } else {
                Swal.fire({
                    icon: 'error',
                    title: 'Oops...',
                    text: text,
                })
            }
        })
})

$("#enter_api").on("click", function() {
    check_can_add();
    auth();
    skip_creds = true;
    $("#get_started, #enter_api, .description").hide();
    $("#block_api_id, #block_api_hash, #block_phone, #block_custom_bot").css("display", "block");
    $("#continue_btn, #denyqr").css("display", "flex");
    $(".api_id").on("input", function() {
        api_id = $(".api_id").val();
        if (api_id.length > 0 && api_hash.length > 0) {
            fetch("/set_api", {
                method: "PUT",
                body: api_hash + api_id,
                credentials: "include"
            })
        }
    })

    $(".api_hash").on("input", function() {
        api_hash = $(".api_hash").val();
        if (api_id.length > 0 && api_hash.length > 0) {
            fetch("/set_api", {
                method: "PUT",
                body: api_hash + api_id,
                credentials: "include"
            })
        }
    })
})

function init_qr() {
    const qrCode = new QRCodeStyling({
        width: 150,
        height: 150,
        type: "svg",
        data: "",
        dotsOptions: {
            color: "#8774e1",
            type: "rounded"
        },
        backgroundOptions: {
            color: "transparent",
        },
        imageOptions: {
            crossOrigin: "anonymous",
            margin: 5
        }
    });

    qrCode.append(document.querySelector(".qr_inner"));

    function qr_updater() {
        fetch("/get_qr_url", {
                method: "POST",
                credentials: "include"
            })
            .then(response => {
                if (response.status == 200) {
                    $(".auth-code-form").fadeOut(200);
                    $(".installation").fadeOut(200);
                    $(".finish_block").fadeIn(200);
                    lottie.loadAnimation({
                        container: document.getElementById('installation_icon'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: 'https://static.dan.tatar/finish.json'
                    });
                    fetch("/finish_login", {
                        method: "POST",
                        credentials: "include"
                    })
                } else if (response.status == 201) {
                    response.text().then((text) => {
                        qrCode.update({
                            data: text
                        })
                    })
                } else if (response.status == 403) {
                    $(".main").fadeOut(200);
                    $(".auth-code-form").fadeIn(200);
                    $(".code-input").attr("placeholder", "••••••••••••••••");
                    $(".code-caption").text("Enter your 2FA password")
                    $(".enter").removeClass("tgcode")
                    lottie.loadAnimation({
                        container: document.getElementById('monkey'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: 'https://static.dan.tatar/monkey.json'
                    });
                    lottie.loadAnimation({
                        container: document.getElementById('monkey-close'),
                        renderer: 'svg',
                        loop: true,
                        autoplay: true,
                        path: 'https://static.dan.tatar/monkey_close.json'
                    });
                } else {
                    response.text().then((text) => {
                        Swal.fire({
                            icon: 'error',
                            title: 'Oops...',
                            text: text,
                        })
                    })
                }
            })
    }
    setInterval(qr_updater, 1000);
}