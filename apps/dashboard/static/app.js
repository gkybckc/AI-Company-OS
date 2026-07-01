// AI Company OS - CEO Control Center

// Update poll indicator text whenever HTMX fires a request
document.addEventListener("htmx:beforeRequest", function (evt) {
  var indicator = document.getElementById("poll-status") ||
                  document.getElementById("events-poll-status");
  if (indicator) {
    indicator.textContent = "refreshing...";
  }
});

document.addEventListener("htmx:afterRequest", function (evt) {
  var indicator = document.getElementById("poll-status") ||
                  document.getElementById("events-poll-status");
  if (indicator) {
    var now = new Date();
    var ts = now.getHours().toString().padStart(2, "0") + ":" +
             now.getMinutes().toString().padStart(2, "0") + ":" +
             now.getSeconds().toString().padStart(2, "0");
    indicator.textContent = "updated " + ts;
  }
});

// Render event rows returned by /api/events/recent into the timeline
document.addEventListener("htmx:afterSwap", function (evt) {
  var target = evt.detail.target;
  if (
    target &&
    (target.id === "event-timeline" || target.id === "live-event-feed")
  ) {
    var raw = target.getAttribute("data-raw") || "";
    if (!raw) return;

    try {
      var events = JSON.parse(raw);
      target.innerHTML = events
        .map(function (ev) {
          var ch = (ev.channel || "").toLowerCase();
          var action = ev.action || "";
          return (
            '<div class="event-item">' +
            '<span class="event-channel event-channel-' + ch + '">' + (ev.channel || "") + "</span>" +
            '<span class="event-source">' + (ev.source || "") + "</span>" +
            '<span class="event-action">' + action + "</span>" +
            "</div>"
          );
        })
        .join("");
    } catch (e) {
      // JSON parse errors are ignored; HTMX already swapped the HTML
    }
  }
});
