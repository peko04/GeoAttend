import QrScanner from
    "https://cdn.jsdelivr.net/npm/qr-scanner@1.4.2/qr-scanner.min.js";


const popup = document.getElementById("scannerPopup");
const video = document.getElementById("qrVideo");

const openButton =
    document.getElementById("openScannerButton");

const navigationButton =
    document.getElementById("scanNavigation");

const closeButton =
    document.getElementById("closeScannerButton");

const startButton =
    document.getElementById("startScannerButton");

const stopButton =
    document.getElementById("stopScannerButton");

const scannerMessage =
    document.getElementById("scannerMessage");

const scannerResult =
    document.getElementById("scannerResult");


let codeAlreadyScanned = false;


/*
    This function runs when a QR code is found.
*/
function handleScanResult(result) {

    if (codeAlreadyScanned) {
        return;
    }

    codeAlreadyScanned = true;

    const qrContent = result.data;

    scannerMessage.textContent =
        "QR code scanned successfully!";

    scannerMessage.className =
        "scanner-message scanner-success";

    scannerResult.textContent =
        "QR content: " + qrContent;

    scannerResult.classList.add("show");

    qrScanner.stop();

    startButton.disabled = false;
    startButton.textContent = "Scan Again";

    stopButton.disabled = true;

    console.log("Scanned QR code:", qrContent);


    // =====================================================
    // AVASH - GPS INTEGRATION POINT
    // After the QR code is successfully scanned,
    // begin collecting the student's GPS location.
    // =====================================================

    getLocation();
}


/*
    Create the camera scanner.
*/
const qrScanner = new QrScanner(
    video,
    handleScanResult,
    {
        preferredCamera: "environment",
        highlightScanRegion: true,
        highlightCodeOutline: true,
        returnDetailedScanResult: true
    }
);


/*
    Open the scanner popup.
*/
function openScannerPopup() {

    popup.classList.add("show");

    scannerMessage.textContent =
        "Press Start Camera and allow camera permission.";

    scannerMessage.className =
        "scanner-message";

    scannerResult.textContent = "";
    scannerResult.classList.remove("show");

    codeAlreadyScanned = false;
}


/*
    Close the popup and turn the camera off.
*/
function closeScannerPopup() {

    qrScanner.stop();

    popup.classList.remove("show");

    startButton.disabled = false;
    startButton.textContent = "Start Camera";

    stopButton.disabled = true;

    codeAlreadyScanned = false;
}


/*
    Start the phone or computer camera.
*/
async function startCamera() {

    try {

        codeAlreadyScanned = false;

        scannerResult.textContent = "";
        scannerResult.classList.remove("show");

        scannerMessage.textContent =
            "Starting camera...";

        startButton.disabled = true;

        await qrScanner.start();

        scannerMessage.textContent =
            "Point the camera at the teacher's QR code.";

        scannerMessage.className =
            "scanner-message";

        stopButton.disabled = false;

    } catch (error) {

        console.error(error);

        scannerMessage.textContent =
            "Camera could not start. Allow camera permission and try again.";

        scannerMessage.className =
            "scanner-message scanner-error";

        startButton.disabled = false;
        stopButton.disabled = true;
    }
}


/*
    Stop the camera without closing the popup.
*/
function stopCamera() {

    qrScanner.stop();

    scannerMessage.textContent =
        "Camera stopped.";

    startButton.disabled = false;
    startButton.textContent = "Start Camera";

    stopButton.disabled = true;
}


/*
    Button events
*/
openButton.addEventListener(
    "click",
    openScannerPopup
);

navigationButton.addEventListener(
    "click",
    function (event) {
        event.preventDefault();
        openScannerPopup();
    }
);

closeButton.addEventListener(
    "click",
    closeScannerPopup
);

startButton.addEventListener(
    "click",
    startCamera
);

stopButton.addEventListener(
    "click",
    stopCamera
);


/*
    Close when the dark background is clicked.
*/
popup.addEventListener(
    "click",
    function (event) {

        if (event.target === popup) {
            closeScannerPopup();
        }
    }
);


/*
    Stop the camera if the student leaves the page.
*/
window.addEventListener(
    "beforeunload",
    function () {
        qrScanner.destroy();
    }
);


// =========================================================
// AVASH - GPS / GEOLOCATION INTEGRATION
// =========================================================
//
// Added for the GeoAttend MVP integration.
//
// Flow:
//
// Successful QR Scan
//      ↓
// Browser Geolocation API
//      ↓
// Latitude + Longitude + Accuracy
//      ↓
// POST /location/validate
//      ↓
// Flask Backend
//      ↓
// Coordinates returned to frontend
//
// NOTE:
// This stage only proves that GPS information can travel
// successfully from the student's browser to Flask.
//
// Classroom coordinates, allowed radius and geofence
// validation will be handled by the backend/database
// integration separately.
// =========================================================


/*
    AVASH - Request student's current GPS location.
*/
function getLocation() {

    if (!navigator.geolocation) {

        scannerMessage.textContent =
            "Geolocation is not supported by this browser.";

        scannerMessage.className =
            "scanner-message scanner-error";

        return;
    }

    scannerMessage.textContent =
        "QR verified. Getting your location...";

    scannerMessage.className =
        "scanner-message";

    navigator.geolocation.getCurrentPosition(
        sendLocationToFlask,
        showLocationError,
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}


/*
    AVASH - Send student's GPS coordinates to Flask.
*/
async function sendLocationToFlask(position) {

    const latitude =
        position.coords.latitude;

    const longitude =
        position.coords.longitude;

    const accuracy =
        position.coords.accuracy;


    console.log(
        "Student GPS:",
        latitude,
        longitude,
        accuracy
    );


    try {

        const response =
            await fetch("/location/validate", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude,
                    accuracy: accuracy
                })
            });


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message ||
                "Location request failed."
            );
        }


        console.log(
            "Flask received location:",
            data
        );


        scannerMessage.textContent =
            "Location successfully sent to Flask.";

        scannerMessage.className =
            "scanner-message scanner-success";


        scannerResult.innerHTML =
            "<strong>GPS received by Flask</strong>" +
            "<br><br>Latitude: " +
            data.latitude +
            "<br>Longitude: " +
            data.longitude +
            "<br>Accuracy: ±" +
            Math.round(data.accuracy) +
            " metres";


        scannerResult.classList.add("show");


    } catch (error) {

        console.error(
            "GPS to Flask error:",
            error
        );


        scannerMessage.textContent =
            "Could not send location to Flask.";

        scannerMessage.className =
            "scanner-message scanner-error";
    }
}


/*
    AVASH - Handle browser GPS/location errors.
*/
function showLocationError(error) {

    let message;


    switch (error.code) {

        case error.PERMISSION_DENIED:

            message =
                "Location permission was denied.";

            break;


        case error.POSITION_UNAVAILABLE:

            message =
                "Your location is currently unavailable.";

            break;


        case error.TIMEOUT:

            message =
                "Location request timed out.";

            break;


        default:

            message =
                "Unable to retrieve your location.";
    }


    console.error(
        "GPS error:",
        error
    );


    scannerMessage.textContent =
        message;

    scannerMessage.className =
        "scanner-message scanner-error";
}