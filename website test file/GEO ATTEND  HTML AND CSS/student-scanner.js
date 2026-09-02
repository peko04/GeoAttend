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

    /*
        Later, this QR content will be sent to the
        Flask backend to record attendance.
    */

    console.log("Scanned QR code:", qrContent);
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

    scannerMessage.className = "scanner-message";

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

        scannerMessage.className = "scanner-message";

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

    scannerMessage.textContent = "Camera stopped.";

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