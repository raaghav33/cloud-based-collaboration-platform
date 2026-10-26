// Small enhancement: auto-dismiss success/info alerts after a short delay.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert-success, .alert-info").forEach((alert) => {
    window.setTimeout(() => {
      if (window.bootstrap) {
        const instance = bootstrap.Alert.getOrCreateInstance(alert);
        instance.close();
      }
    }, 4500);
  });
});
