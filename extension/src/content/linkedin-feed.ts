import { initializeLinkedInCapture } from "./injector";

const capturedFrom =
  window.location.pathname.includes("/posts/") ||
  window.location.pathname.includes("/feed/update/")
    ? "post_detail"
    : "feed";

initializeLinkedInCapture(capturedFrom);
