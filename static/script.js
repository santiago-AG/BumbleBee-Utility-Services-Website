function showEmail() {
  document.getElementById("email").innerText = "bumblebeegardening@gmail.com";
}

document.addEventListener("DOMContentLoaded", () => {
  const calendarEl = document.getElementById("calendar");
  const timeSlotsDiv = document.getElementById("timeSlots");
  const form = document.getElementById("bookingForm");

  // Initialize FullCalendar
const calendar = new FullCalendar.Calendar(calendarEl, {
  initialView: "dayGridMonth",
  weekends: true, // show weekends (but disable booking)
  events: "/calendar",

  // 🩶 Style past days + weekends
  dayCellDidMount: function (info) {
    const today = new Date();
    const cellDate = new Date(info.date);
    const day = cellDate.getUTCDay(); // Sunday=0 ... Saturday=6

    if (cellDate < today.setHours(0, 0, 0, 0)) {
      info.el.style.backgroundColor = "#a9a9a9"; // dark grey for past
      info.el.style.opacity = "0.7";
    } else if (day === 0 || day === 6) {
      info.el.style.backgroundColor = "#d3d3d3"; // light grey for weekends
      info.el.style.opacity = "0.8";
    }
  },

  // 🟢 Handle clicks
  dateClick: async (info) => {
    const date = info.dateStr;
    const clickedDate = new Date(date);
    const today = new Date();
    const day = clickedDate.getUTCDay(); // Sunday=0, Saturday=6

    // 🩶 Prevent booking on past days or weekends
    if (clickedDate < today.setHours(0, 0, 0, 0)) {
      timeSlotsDiv.innerHTML = `<h3>${date}</h3><p>You can’t book past dates.</p>`;
      form.style.display = "none";
      return;
    }

    if (day === 0 || day === 6) {
      timeSlotsDiv.innerHTML = `<h3>${date}</h3><p>Bookings are only available Monday to Friday.</p>`;
      form.style.display = "none";
      return;
    }

    // Helper to format YYYY-MM-DD -> DD/MM/YYYY
    function formatDisplayDate(isoDate) {
      const [year, month, day] = isoDate.split("-");
      return `${day}/${month}/${year}`;
    }

    // Fetch availability for the clicked date
    const response = await fetch(`/availability/${date}`);
    const data = await response.json();

    const displayDate = formatDisplayDate(date);
    timeSlotsDiv.innerHTML = `<h3>Available Times for ${displayDate}</h3>`;

    if (data.available.length === 0) {
      timeSlotsDiv.innerHTML += "<p>No availability</p>";
      return;
    }

    data.available.forEach(time => {
      const btn = document.createElement("button");
      btn.textContent = time;
      btn.type = "button";
      btn.addEventListener("click", () => {
        form.style.display = "block";
        form.date.value = date;
        form.time.value = time;
      });
      timeSlotsDiv.appendChild(btn);
    });
  }
});


  calendar.render();

  // Handle booking form
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = {
      name: form.name.value,
      email: form.email.value,
      date: form.date.value,
      time: form.time.value
    };

    const response = await fetch("/book", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData)
    });

    const result = await response.json();
    alert(result.message);

    if (result.status === "success") {
      form.reset();
      form.style.display = "none";
      timeSlotsDiv.innerHTML = "";
      calendar.refetchEvents(); // refresh calendar
    }
  });
});
