var api_id;
var api_hash;
var phone;
var password;
var custom_bot;
var qr_login = false;

var state = 0;
var tg_code_hash;

$(document).on("keydown", "input", function (e) {
  if (e.which == 13) {
    if (state == 0) {
      $("#continue_btn").click();
    } else {
      $(".enter").click();
    }
  }
});

$("#get_started").click(function () {
  $("#get_started").fadeOut(100);
  $("#enter_api").fadeOut(100, function () {
    $("#block_phone").fadeIn(200);
    $("#continue_btn").fadeIn(200);
    if (!skip_creds) {
      $("#denyqr").fadeIn(200);
    }
  });
});

$("#enter_api").click(function () {
  $("#get_started").fadeOut(100);
  $("#enter_api").fadeOut(100, function () {
    $("#block_api_id").fadeIn(200);
    $("#block_api_hash").fadeIn(200);
    $("#block_phone").fadeIn(200);
    $("#continue_btn").fadeIn(200);
    if (!skip_creds) {
      $("#denyqr").fadeIn(200);
    }
  });
});


$("#denyqr").click(function () {
  qr_login = false;
  $("#block_qr_login").fadeOut(200);
  $("#denyqr").fadeOut(200, function () {
    $("#block_phone").fadeIn(200);
    $("#continue_btn").fadeIn(200);
  });
});

$("#continue_btn").click(async function () {
  let body_payload = "";

  if ($("#api_id").val() && $("#api_hash").val()) {
    api_id = $("#api_id").val();
    api_hash = $("#api_hash").val();

    if (api_hash.length != 32) {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: 'Invalid API hash',
        background: "#16181d",
        color: "#fff"
      });
      return;
    }

    if (isNaN(parseInt(api_id))) {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: 'Invalid API ID',
        background: "#16181d",
        color: "#fff"
      });
      return;
    }

    body_payload = api_hash + api_id;
  }

  let r = await fetch("/set_api", {
    method: "PUT",
    body: body_payload,
    credentials: "include"
  });

  if (r.status != 200) {
    Swal.fire({
      icon: 'error',
      title: 'Oops...',
      text: await r.text(),
      background: "#16181d",
      color: "#fff"
    });
    return;
  }

  skip_creds = true;


  if ($("#phone").val()) {
    phone = $("#phone").val();

    if (!phone.match(/^\+?[0-9]{1,15}$/)) {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: 'Invalid phone number',
        background: "#16181d",
        color: "#fff"
      });
      return;
    }

    let r = await fetch("/send_tg_code", {
      method: "POST",
      body: phone,
      credentials: "include"
    });

    if (r.status != 200) {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: await r.text(),
        background: "#16181d",
        color: "#fff"
      });
      return;
    }
  }

  if ($("#custom_bot").val()) {
    custom_bot = $("#custom_bot").val();

    let r = await fetch("/custom_bot", {
      method: "POST",
      body: custom_bot,
      credentials: "include"
    });
    let rt = await r.text();

    if (r.status != 200 || rt != "OK") {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: rt == "OCCUPIED" ? "Username occupied or invalid" : "Error while setting custom bot username",
        background: "#16181d",
        color: "#fff"
      });
      return;
    }
  }

  if (qr_login) {
    if ($("#block_qr_login").is(':hidden')) {
      $("#continue_btn").fadeOut(200);
      $("#denyqr").fadeOut(200);
      $("#block_phone").fadeOut(200, function () {
        $("#block_qr_login").fadeIn(200, function () {
          qr_code.update({
            data: qr_url
          })
        });
      });
    }
  } else {
    state = 1;
    $(".main").fadeOut(200, function () {
      $(".auth-code-form").fadeIn(200);
    });
  }
});

$(".enter").click(async function () {
  if (state == 1) {
    let r = await fetch("/tg_code", {
      method: "POST",
      body: $(".code-input").val() + "\n" + phone,
      credentials: "include"
    });

    let rt = await r.text();

    if (r.status == 401) {
      state = 2;
      $(".code-caption").text(rt);
      $(".code-input").val("");
      $("#monkey").fadeOut(200, function () {
        $("#monkey-close").fadeIn(200);
      });
      $(".enter").addClass("tgcode");
      return;
    }

    if (r.status != 200) {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: rt,
        background: "#16181d",
        color: "#fff"
      });
      return;
    }
  } else {
    let r = await fetch("/tg_code", {
      method: "POST",
      body: "0\n" + phone + "\n" + $(".code-input").val(),
      credentials: "include"
    });

    if (r.status != 200) {
      Swal.fire({
        icon: 'error',
        title: 'Oops...',
        text: await r.text(),
        background: "#16181d",
        color: "#fff"
      });
      return;
    }
  }
  state = 0;
  $(".auth-code-form").fadeOut(200, function () {
    $(".main.installation").fadeOut(200);
    $(".main.finish_block").fadeIn(200);
  });
  fetch("/finish_login", {
    method: "POST",
    credentials: "include"
  })
});

var animation = bodymovin.loadAnimation({
  container: document.getElementById('tg_icon'),
  renderer: 'svg',
  loop: true,
  autoplay: true,
  path: 'https://static.dan.tatar/telegram_loader.json'
})

var animation2 = bodymovin.loadAnimation({
  container: document.getElementById('installation_icon'),
  renderer: 'svg',
  loop: true,
  autoplay: true,
  path: 'https://static.dan.tatar/installation_done.json'
})

var animation3 = bodymovin.loadAnimation({
  container: document.getElementById('monkey'),
  renderer: 'svg',
  loop: true,
  autoplay: true,
  path: 'https://static.dan.tatar/monkey.json'
})

var animation4 = bodymovin.loadAnimation({
  container: document.getElementById('monkey-close'),
  renderer: 'svg',
  loop: true,
  autoplay: true,
  path: 'https://static.dan.tatar/monkey_close.json'
})

var animation5 = bodymovin.loadAnimation({
  container: document.getElementById('law'),
  renderer: 'svg',
  loop: true,
  autoplay: true,
  path: 'https://static.dan.tatar/law.json'
})

if (auth_required) {
  $(document).ready(function () {
    $(".auth").fadeIn(200);
    $.cookie('session', 'unauthorized', {
      expires: 1,
      path: '/'
    });
    fetch("/web_auth", {
      method: "POST",
      credentials: "include"
    }).then(response => response.text()).then((response) => {
      if (response != "TIMEOUT") {
        $.cookie('session', response, {
          expires: 1,
          path: '/'
        });
        $(".auth").fadeOut(200);
        check_can_add();
      }
    })
  });
} else {
  check_can_add();
}


var qr_url;

const qr_code = new QRCodeStyling({
  width: 150,
  height: 150,
  type: "svg",
  image: "https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/heroku.png",
  dotsOptions: {
    color: "#000",
    type: "rounded"
  },
  backgroundOptions: {
    color: "rgba(255, 255, 255, 0)",
  },
  imageOptions: {
    crossOrigin: "anonymous",
    margin: 5
  }
});

qr_code.append(document.querySelector(".qr_inner"));

async function qr_tick() {
  let r = await fetch("/get_qr_url", {
    method: "POST",
    credentials: "include"
  });

  if (r.status == 201) {
    let url = await r.text();
    if (url != qr_url) {
      qr_url = url;
      qr_code.update({
        data: qr_url
      })
    }
  } else if (r.status == 200) {
    if ($("#block_2fa").is(':hidden')) {
      $(".qr_outer").fadeOut(200);
      $(".tg_guide").fadeOut(200, function () {
        $("#block_2fa").fadeIn(200);
      });
    }
    return;
  } else if (r.status == 403) {
    if ($("#block_2fa").is(':hidden')) {
      $(".qr_outer").fadeOut(200);
      $(".tg_guide").fadeOut(200, function () {
        $("#block_2fa").fadeIn(200);
      });
    }
    return;
  }

  setTimeout(qr_tick, 1000);
}

function check_can_add() {
  fetch("/can_add", {
    method: "POST",
    credentials: "include"
  }).then(response => {
    if (response.status == 403) {
      $(".main.installation").fadeOut(200, function () {
        $(".eula-form").fadeIn(200);
      })
    }
  });
}