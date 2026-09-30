const message = document.getElementById('message');
const start = document.getElementById('start');
const scanUrl = message.dataset.scanUrl;

let scanner;
let scanned = false;


// ==========================================
// GET STUDENT LOCATION
// ==========================================

function getLocation() {

    return new Promise((resolve, reject) => {

        if (!navigator.geolocation) {
            reject(new Error('Location is not supported.'));
            return;
        }

        navigator.geolocation.getCurrentPosition(
            resolve,
            reject,
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );

    });

}


// ==========================================
// START QR SCANNER
// ==========================================

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
            message.textContent =
                'Point the camera at the QR code.';
        }

    } catch (error) {

        console.error(error);

        message.textContent =
            'Camera unavailable. Check camera permission.';

        start.disabled = false;

    }

};


// ==========================================
// QR SCANNED
// ==========================================

async function saveAttendance(result) {

    if (scanned) return;

    scanned = true;

    scanner.stop();

    message.textContent =
        'QR scanned. Checking your location...';

    try {

        // Get student's current GPS location
        const position = await getLocation();

        const latitude =
            position.coords.latitude;

        const longitude =
            position.coords.longitude;


        console.log(
            'Student location:',
            latitude,
            longitude
        );


        // Send QR token + student location to Flask
        const response = await fetch(
            scanUrl,
            {
                method: 'POST',

                headers: {
                    'Content-Type': 'application/json'
                },

                body: JSON.stringify({
                    token: result.data,
                    latitude: latitude,
                    longitude: longitude
                })
            }
        );


        const data = await response.json();

        message.textContent = data.message;


        // Attendance successfully recorded
        if (data.success) {

            alert(data.message);

            location.reload();

        }

    } catch (error) {

        console.error(
            'Location/check-in error:',
            error
        );

        message.textContent =
            'Could not get your location. ' +
            'Please allow location permission and try again.';

    }


    start.disabled = false;

}


// ==========================================
// STOP CAMERA
// ==========================================

document.getElementById('stop').onclick = () => {

    if (scanner) {
        scanner.stop();
    }

    start.disabled = false;

};


// ==========================================
// STOP CAMERA WHEN PAGE CLOSES
// ==========================================

window.addEventListener('pagehide', () => {

    if (scanner) {
        scanner.stop();
    }

});