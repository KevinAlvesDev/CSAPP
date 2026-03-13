(function () {
  "use strict";

  var body = document.body;
  if (body && body.dataset && body.dataset.currentContext) {
    window.currentContext = body.dataset.currentContext;
  }

  function showFlashToasts() {
    var node = document.getElementById("flash-messages-json");
    if (!node) return;

    var payload = [];
    try {
      payload = JSON.parse(node.textContent || "[]");
    } catch (e) {
      return;
    }

    var typeMap = {
      success: "success",
      error: "error",
      danger: "error",
      warning: "warning",
      info: "info",
      primary: "primary",
    };

    payload.forEach(function (msg) {
      var category = msg[0];
      var message = msg[1];
      var toastType = typeMap[category] || "info";
      if (window.showToast) {
        window.showToast(message, toastType, 6000);
      }
    });
  }

  function syncProfileFromHtmx(evt) {
    if (!evt || !evt.detail || !evt.detail.xhr) return;

    var photoUrl = evt.detail.xhr.getResponseHeader("X-Updated-Photo-Url");
    var userName = evt.detail.xhr.getResponseHeader("X-Updated-Name");

    if (photoUrl) {
      var photoElements = document.querySelectorAll(".user-photo-global, .profile-avatar__image, #sidebar-user-photo");
      photoElements.forEach(function (img) {
        img.src = photoUrl + "?v=" + new Date().getTime();
      });

      var fallbacks = document.querySelectorAll(".profile-avatar__fallback, .user-avatar-fallback");
      fallbacks.forEach(function (div) {
        var parent = div.parentNode;
        if (!parent) return;

        var newImg = document.createElement("img");
        newImg.src = photoUrl;
        newImg.className = div.className.replace("fallback", "image") + " rounded-circle";
        newImg.style.width = "100%";
        newImg.style.height = "100%";
        newImg.style.objectFit = "cover";
        parent.replaceChild(newImg, div);
      });
    }

    if (userName) {
      var nameElements = document.querySelectorAll(".user-name-global, #sidebar-user-name");
      nameElements.forEach(function (el) {
        el.textContent = userName;
      });
    }
  }

  window.previewImage = function (input, previewId, fallbackId, containerId) {
    if (!(input && input.files && input.files[0])) return;

    var reader = new FileReader();
    reader.onload = function (e) {
      var result = e && e.target ? e.target.result : null;
      if (!result) return;

      var previewImg = document.getElementById(previewId);
      var fallback = document.getElementById(fallbackId);

      if (previewImg) {
        previewImg.src = result;
        if (previewImg.tagName === "DIV") {
          previewImg.style.backgroundImage = "url(" + result + ")";
        }
        return;
      }

      if (!fallback) return;
      var container = document.getElementById(containerId);
      if (!container) return;

      var img = document.createElement("img");
      img.id = previewId;
      img.src = result;
      img.className = fallback.className.replace("fallback", "image");
      img.style.width = "100%";
      img.style.height = "100%";
      img.style.objectFit = "cover";
      container.replaceChild(img, fallback);
    };
    reader.readAsDataURL(input.files[0]);
  };

  document.addEventListener("DOMContentLoaded", showFlashToasts);
  document.addEventListener("htmx:afterRequest", syncProfileFromHtmx);
})();
