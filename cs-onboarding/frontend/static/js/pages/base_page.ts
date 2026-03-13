type FlashMessage = [string, string];

function showFlashToasts(): void {
  const node = document.getElementById("flash-messages-json");
  if (!node) return;

  let payload: FlashMessage[] = [];
  try {
    payload = JSON.parse(node.textContent || "[]") as FlashMessage[];
  } catch {
    return;
  }

  const typeMap: Record<string, string> = {
    success: "success",
    error: "error",
    danger: "error",
    warning: "warning",
    info: "info",
    primary: "primary",
  };

  payload.forEach(([category, message]) => {
    const toastType = typeMap[category] || "info";
    if ((window as any).showToast) {
      (window as any).showToast(message, toastType, 6000);
    }
  });
}

function syncProfileFromHtmx(evt: Event): void {
  const detail = (evt as any).detail;
  if (!detail?.xhr) return;

  const photoUrl = detail.xhr.getResponseHeader("X-Updated-Photo-Url");
  const userName = detail.xhr.getResponseHeader("X-Updated-Name");

  if (photoUrl) {
    const photoElements = document.querySelectorAll<HTMLImageElement>(
      ".user-photo-global, .profile-avatar__image, #sidebar-user-photo",
    );
    photoElements.forEach((img) => {
      img.src = `${photoUrl}?v=${new Date().getTime()}`;
    });
  }

  if (userName) {
    const nameElements = document.querySelectorAll<HTMLElement>(".user-name-global, #sidebar-user-name");
    nameElements.forEach((el) => {
      el.textContent = userName;
    });
  }
}

export function initBasePage(): void {
  const body = document.body;
  if (body?.dataset?.currentContext) {
    (window as any).currentContext = body.dataset.currentContext;
  }

  document.addEventListener("DOMContentLoaded", showFlashToasts);
  document.addEventListener("htmx:afterRequest", syncProfileFromHtmx as EventListener);
}

