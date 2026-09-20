const qrCode = document.getElementById('qrcode');

if (qrCode) {
    new QRCode(qrCode, {
        text: qrCode.dataset.token,
        width: 200,
        height: 200
    });
}