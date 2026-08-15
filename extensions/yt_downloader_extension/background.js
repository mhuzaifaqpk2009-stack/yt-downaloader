chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "open-with-yt-downloader",
    title: "Open with YT Downloader",
    // show on any right-click context on YouTube pages (page, links, images, video, etc.)
    contexts: ["all"],
    // match any YouTube page (watch, shorts, youtu.be, channel pages, etc.)
    documentUrlPatterns: [
      "*://*.youtube.com/*",
      "*://youtu.be/*"
    ]
  });
});

function isYouTubeVideoUrl(url) {
  if (!url) return false;
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    if (host === 'youtu.be') return true;
    if (host === 'youtube.com' || host.endsWith('.youtube.com')) {
      if (parsed.pathname === '/watch') return true;
      if (parsed.pathname.startsWith('/shorts/')) return true;
    }
    return false;
  } catch (e) {
    return false;
  }
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab || typeof tab.id === 'undefined') return;
  const linkUrl = info.linkUrl;
  chrome.tabs.get(tab.id, (currentTab) => {
    if (chrome.runtime.lastError || !currentTab || !currentTab.url) return;
    const chosenUrl = (linkUrl && isYouTubeVideoUrl(linkUrl)) ? linkUrl : currentTab.url;
    try {
      chrome.runtime.sendNativeMessage('com.yt_downloader.host', { url: chosenUrl, fetch: true }, () => {
        // Fire-and-forget: the native host forwards the URL to the running app.
      });
    } catch (e) {
      console.warn('Native Messaging failed:', e);
    }
  });
});
