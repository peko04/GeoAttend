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

// Find every attendance dropdown on the teacher page
const attendanceDropdowns =
    document.querySelectorAll('.attendance-dropdown');


// Listen for the teacher changing a dropdown
attendanceDropdowns.forEach(dropdown => {

    dropdown.addEventListener('change', async function () {

        const studentId = this.dataset.studentId;
        const subjectId = this.dataset.subjectId;
        const week = this.dataset.week;
        const status = this.value;

        try {

            const response = await fetch('/attendance/update', {

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

            });


            const result = await response.json();


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
