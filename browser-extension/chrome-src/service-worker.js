import {
  saveArticle,
  listTags,
  updateArticle,
  subscribeToFeed,
  updateFeed,
  listCategories,
} from "./legadilo.js";

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  onMessage(request, sender, sendResponse);

  return true;
});

const onMessage = async (request, sender, sendResponse) => {
  try {
    switch (request.name) {
      case "save-article":
        await processSaveArticleRequest(sendResponse, request.payload);
        break;
      case "update-article":
        await processUpdateArticleRequest(sendResponse, request.articleId, request.payload);
        break;
      case "subscribe-to-feed":
        await processFeedSubscriptionRequest(sendResponse, request.payload);
        break;
      case "update-feed":
        await processUpdateFeedRequest(sendResponse, request.feedId, request.payload);
        break;
      default:
        console.warn(`Unknown action ${request.name}`);
        break;
    }
  } catch (err) {
    sendResponse({ error: err.message });
  }
};

const processSaveArticleRequest = async (sendResponse, payload) => {
  const article = await saveArticle(payload);
  const tags = await listTags();
  sendResponse({ name: "saved-article", article, tags });
};

const processUpdateArticleRequest = async (sendResponse, articleId, payload) => {
  const article = await updateArticle(articleId, payload);
  const tags = await listTags();
  sendResponse({ name: "updated-article", article, tags });
};

const processFeedSubscriptionRequest = async (sendResponse, payload) => {
  const feed = await subscribeToFeed(payload.link);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  sendResponse({ name: "subscribed-to-feed", feed, tags, categories });
};

const processUpdateFeedRequest = async (sendResponse, feedId, payload) => {
  const feed = await updateFeed(feedId, payload);
  const [tags, categories] = await Promise.all([listTags(), listCategories()]);
  sendResponse({ name: "updated-feed", feed, tags, categories });
};
