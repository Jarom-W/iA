document.querySelectorAll("[data-auto-dismiss]").forEach(notice => {
  setTimeout(() => notice.remove(), 3000);
});
