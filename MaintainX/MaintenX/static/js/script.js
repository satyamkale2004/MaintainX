// ---------------- ALERT MESSAGE ----------------

function showAlert(message, type="success") {
    const alertBox = document.createElement("div");
    alertBox.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    alertBox.style.zIndex = "9999";
    alertBox.innerText = message;

    document.body.appendChild(alertBox);

    setTimeout(() => {
        alertBox.remove();
    }, 3000);
}


// ---------------- CONFIRM DELETE ----------------

function confirmDelete() {
    return confirm("Are you sure you want to delete?");
}


// ---------------- FORM VALIDATION ----------------

function validateForm() {

    let inputs = document.querySelectorAll("input[required]");

    for (let input of inputs) {
        if (input.value.trim() === "") {
            showAlert("Please fill all required fields", "danger");
            return false;
        }
    }

    return true;
}


// ---------------- SEARCH FILTER ----------------

function searchTable() {
    let input = document.getElementById("searchInput");
    let filter = input.value.toLowerCase();

    let rows = document.querySelectorAll("table tbody tr");

    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? "" : "none";
    });
}


// ---------------- AUTO HIDE FLASH MESSAGE ----------------

window.onload = function () {
    let flash = document.getElementById("flash-msg");

    if (flash) {
        setTimeout(() => {
            flash.style.display = "none";
        }, 3000);
    }
};


// ---------------- SIMPLE LOADER ----------------

function showLoader() {
    document.getElementById("loader").style.display = "block";
}

function hideLoader() {
    document.getElementById("loader").style.display = "none";
}