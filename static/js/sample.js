// canvas
var can;
var ct;
var ox = 0, oy = 0, x = 0, y = 0;
var mf = false;

window.onload = () => {mam_draw_init()}
function mam_draw_init() {
    can = document.getElementById("can");
    can.addEventListener("touchstart", onDown, false);
    can.addEventListener("touchmove", onMove, false);
    can.addEventListener("touchend", onUp, false);
    can.addEventListener("mousedown", onMouseDown, false);
    can.addEventListener("mousemove", onMouseMove, false);
    can.addEventListener("mouseup", onMouseUp, false);
    ct = can.getContext("2d");
    ct.strokeStyle = "#000000";
    ct.lineWidth = 15;
    ct.lineJoin = "round";
    ct.lineCap = "round";
    clearCan();
}
function onDown(event) {
    mf = true;
    ox = event.touches[0].pageX - event.target.getBoundingClientRect().left;
    oy = event.touches[0].pageY - event.target.getBoundingClientRect().top;
    event.stopPropagation();
}
function onMove(event) {
    if (mf) {
        x = event.touches[0].pageX - event.target.getBoundingClientRect().left;
        y = event.touches[0].pageY - event.target.getBoundingClientRect().top;
        drawLine();
        ox = x;
        oy = y;
        event.preventDefault();
        event.stopPropagation();
    }
}
function onUp(event) {
    mf = false;
    event.stopPropagation();
}
function onMouseDown(event) {
    ox = event.clientX - event.target.getBoundingClientRect().left;
    oy = event.clientY - event.target.getBoundingClientRect().top;
    mf = true;
}
function onMouseMove(event) {
    if (mf) {
        x = event.clientX - event.target.getBoundingClientRect().left;
        y = event.clientY - event.target.getBoundingClientRect().top;
        drawLine();
        ox = x;
        oy = y;
    }
}
function onMouseUp(event) {
    mf = false;
}
function drawLine() {
    ct.beginPath();
    ct.moveTo(ox, oy);
    ct.lineTo(x, y);
    ct.stroke();
}
function clearCan() {
    ct.fillStyle = "rgb(255,255,255)";
    ct.fillRect(0, 0, can.getBoundingClientRect().width, can.getBoundingClientRect().height);
}
// 画像をajaxに変えてurlに入れている？
function sendImage() {
    var img = document.getElementById("can").toDataURL('image/png');
    const data = JSON.stringify({'img': img}); 
    // img = img.replace('image/png', 'image/octet-stream');
    $.ajax({
        type: "POST",
        url: "/create",
        contentType: 'application/json',
        data: data
    })
    // テキスト　感情回してdataで帰ってくる？
    // $.ajax({
    //     type: "POST",
    //     url: "https://gsfujimurasan.uc.r.appspot.com/",
    //     data: {
    //         "img": img
    //     }
    // })
    
    .done( (data) => {
        $('#answer').html('<span class="answer">'+data['ans']+'</span>')
    });
}

// 日付
document.getElementById("text").innerHTML =  getToday();
function  getToday(){
  var now = new Date();
  var year = now.getFullYear();
  var mon = now.getMonth()+1; 
  var day = now.getDate();
  var you = now.getDay();

  var youbi = new Array("日","月","火","水","木","金","土");
  var s = year + "年" + mon + "月" + day + "日 (" + youbi[you] + ")";
  return s;
}
