// ==========================================
// TEACHER LOCATION + START QR SESSION
// ==========================================

const sessionForm =
    document.querySelector('.teacher-session-form');

if (sessionForm) {

    sessionForm.addEventListener('submit', function (event) {

        // Stop normal form submission temporarily
        event.preventDefault();

        const startButton =
            sessionForm.querySelector('.teacher-start-button');

        if (startButton) {
            startButton.disabled = true;
            startButton.textContent = 'Getting location...';
        }

        // Check if browser supports location
        if (!navigator.geolocation) {

            alert('Location is not supported by this browser.');

            if (startButton) {
                startButton.disabled = false;
                startButton.textContent = 'Start QR Session';
            }

            return;
        }

        // Get teacher's current location
        navigator.geolocation.getCurrentPosition(

            function (position) {

                const latitude =
                    position.coords.latitude;

                const longitude =
                    position.coords.longitude;


                // Create hidden latitude field
                const latitudeInput =
                    document.createElement('input');

                latitudeInput.type = 'hidden';
                latitudeInput.name = 'latitude';
                latitudeInput.value = latitude;


                // Create hidden longitude field
                const longitudeInput =
                    document.createElement('input');

                longitudeInput.type = 'hidden';
                longitudeInput.name = 'longitude';
                longitudeInput.value = longitude;


                // Add location to the form
                sessionForm.appendChild(latitudeInput);
                sessionForm.appendChild(longitudeInput);


                console.log(
                    'Teacher location:',
                    latitude,
                    longitude
                );


                // Submit form to Flask
                sessionForm.submit();
            },

            function (error) {

                console.error(
                    'Location error:',
                    error
                );

                alert(
                    'Could not get your location. ' +
                    'Please allow location permission.'
                );

                if (startButton) {
                    startButton.disabled = false;
                    startButton.textContent = 'Start QR Session';
                }
            },

            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }

        );

    });

}


// ==========================================
// QR CODE
// ==========================================

const qrCode = document.getElementById('qrcode');

if (qrCode) {

    new QRCode(qrCode, {

        text: qrCode.dataset.token,
        width: 200,
        height: 200

    });

}


// ==========================================
// MANUAL ATTENDANCE
// ==========================================

const attendanceDropdowns =
    document.querySelectorAll('.attendance-dropdown');


attendanceDropdowns.forEach(dropdown => {

    dropdown.addEventListener('change', async function () {

        const studentId =
            this.dataset.studentId;

        const subjectId =
            this.dataset.subjectId;

        const week =
            this.dataset.week;

        const status =
            this.value;


        try {

            const response = await fetch(
                '/attendance/update',
                {

                    method: 'POST',

                    headers: {
                        'Content-Type': 'application/json'
                    },

                    body: JSON.stringify({

                        student_id: studentId,
                        subject_id: subjectId,
                        week: week,
                        status: status

                    })

                }
            );


            const result =
                await response.json();


            if (result.success) {

                console.log(
                    'Attendance updated:',
                    studentId,
                    subjectId,
                    week,
                    status
                );

            } else {

                alert(
                    result.message ||
                    'Attendance could not be updated.'
                );

            }

        } catch (error) {

            console.error(
                'Attendance update failed:',
                error
            );

            alert(
                'There was an error updating attendance.'
            );

        }

    });

});