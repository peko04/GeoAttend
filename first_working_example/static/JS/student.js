const message = document.getElementById('message');
const start = document.getElementById('start');
const scanUrl = message.dataset.scanUrl;

let scanner;
let scanned = false;

start.onclick = async () => {
    start.disabled = true;

    try {
        if (!scanner) {
            const {default: QrScanner} = await import(
                'https://cdn.jsdelivr.net/npm/qr-scanner@1.4.2/qr-scanner.min.js'
            );

            scanner = new QrScanner(
                document.getElementById('camera'),
                saveAttendance,
                {
                    preferredCamera: 'environment',
                    returnDetailedScanResult: true
                }
            );
        }

        scanned = false;
        await scanner.start();

        if (!scanned) {
            message.textContent = 'Point the camera at the QR code.';
        }
    } catch (error) {
        message.textContent =
            'Camera unavailable. Check permission, internet, and use localhost or HTTPS.';
        start.disabled = false;
    }
};

async function saveAttendance(result) {
    if (scanned) return;

    scanned = true;
    scanner.stop();

    try {
        const response = await fetch(scanUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({token: result.data})
        });

        const data = await response.json();
        message.textContent = data.message;

        if (data.success) {
            alert(data.message);
            location.reload();
        }
    } catch (error) {
        message.textContent = 'Could not confirm attendance. Refresh to check.';
    }

    start.disabled = false;
}

document.getElementById('stop').onclick = () => {
    if (scanner) scanner.stop();
    start.disabled = false;
};

window.addEventListener('pagehide', () => {
    if (scanner) scanner.stop();
});