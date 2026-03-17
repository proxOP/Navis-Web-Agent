/**
 * Navis content script coordinator for the v1 Python service flow.
 */

const interruptDetector = new InterruptDetector();
const elementHighlighter = new ElementHighlighter();
const navigationController = new NavigationController();
const feedbackCollector = new FeedbackCollector();

const BACKEND_URL = "http://127.0.0.1:8000";
let sessionId = null;
let isActionRunning = false;

function initializeNavis() {
    chrome.runtime.onMessage.addListener(handleMessage);
    console.log("[Navis] Content script initialized");
}

async function handleMessage(message, sender, sendResponse) {
    try {
        switch (message.type) {
            case "navis_run_goal": {
                const result = await runGoal(message.userGoal);
                sendResponse({ success: true, result });
                return true;
            }
            case "navis_get_page_info": {
                sendResponse({ success: true, page: getPageInfo() });
                return true;
            }
            default:
                sendResponse({ success: false, error: `Unknown message type: ${message.type}` });
                return true;
        }
    } catch (error) {
        console.error("[Navis] Message handling error:", error);
        sendResponse({ success: false, error: error.message });
        return true;
    }
}

async function runGoal(userGoal) {
    if (!userGoal || !userGoal.trim()) {
        throw new Error("User goal is required");
    }

    const activeSessionId = await ensureSession();
    const pageContext = getPageInfo();
    const elements = collectInteractiveElements();

    const analysis = await postJson("/semantic/analyze", {
        session_id: activeSessionId,
        user_goal: userGoal.trim(),
        page_context: pageContext,
        elements
    });

    const decision = analysis.decision || {};
    let selected = decision.selected;

    if (decision.requires_confirmation && analysis.candidates?.length) {
        selected = await requestCandidateSelection(analysis.candidates, analysis.intent);
        if (!selected) {
            await postFeedback(userGoal, pageContext, null, "cancelled", "User cancelled selection");
            return {
                ok: false,
                cancelled: true,
                message: "Action cancelled"
            };
        }
    }

    if (!selected) {
        return {
            ok: false,
            message: "No action could be selected",
            analysis
        };
    }

    const result = await executeSelectedAction(selected, analysis.intent);
    await postFeedback(
        userGoal,
        getPageInfo(),
        selected,
        result.success ? "success" : "failed",
        result.message || result.error || null
    );

    if (shouldAskForFeedback(selected, result)) {
        await requestResultFeedback(userGoal, selected);
    }

    return {
        ok: result.success,
        intent: analysis.intent,
        selected,
        result,
        requires_confirmation: !!decision.requires_confirmation
    };
}

async function ensureSession() {
    if (sessionId) {
        return sessionId;
    }

    const response = await postJson("/sessions", {
        metadata: {
            url: window.location.href,
            title: document.title
        }
    });
    sessionId = response.session_id;
    return sessionId;
}

function getPageInfo() {
    return {
        url: window.location.href,
        title: document.title,
        scroll_position: navigationController.getScrollPosition(),
        max_scroll: navigationController.getMaxScrollPosition(),
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight
        }
    };
}

function collectInteractiveElements() {
    const selectors = [
        "button",
        "a[href]",
        "input",
        "select",
        "textarea",
        "[role='button']",
        "[role='link']",
        "[tabindex]",
        "[onclick]"
    ];

    const nodes = Array.from(document.querySelectorAll(selectors.join(",")));
    const seenSelectors = new Set();

    return nodes
        .slice(0, 200)
        .map((node) => buildElementSnapshot(node))
        .filter((element) => {
            if (!element || !element.selector || seenSelectors.has(element.selector)) {
                return false;
            }
            seenSelectors.add(element.selector);
            return true;
        });
}

function buildElementSnapshot(node) {
    const selector = buildSelector(node);
    if (!selector) {
        return null;
    }

    const rect = node.getBoundingClientRect();
    const style = window.getComputedStyle(node);
    const label = (node.getAttribute("aria-label") || "").trim();
    const placeholder = (node.getAttribute("placeholder") || "").trim();
    const nearbyText = extractNearbyText(node);

    return {
        selector,
        tag: node.tagName.toLowerCase(),
        type: (node.getAttribute("type") || "").toLowerCase(),
        role: (node.getAttribute("role") || "").toLowerCase(),
        text: extractElementText(node),
        aria_label: label,
        placeholder,
        nearby_text: nearbyText,
        is_visible: isVisible(node, style, rect),
        is_enabled: !node.disabled && node.getAttribute("aria-disabled") !== "true",
        position: {
            x: Math.round(rect.left + window.scrollX),
            y: Math.round(rect.top + window.scrollY),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
        }
    };
}

function extractElementText(node) {
    const text = (node.innerText || node.textContent || node.value || "").replace(/\s+/g, " ").trim();
    return text.slice(0, 120);
}

function extractNearbyText(node) {
    const parent = node.closest("label, form, section, article, nav, div") || node.parentElement;
    const text = parent ? (parent.innerText || parent.textContent || "") : "";
    return text.replace(/\s+/g, " ").trim().slice(0, 180);
}

function isVisible(node, style, rect) {
    return !!(
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== "hidden" &&
        style.display !== "none"
    );
}

function buildSelector(node) {
    if (node.id) {
        return `#${CSS.escape(node.id)}`;
    }

    const path = [];
    let current = node;

    while (current && current.nodeType === Node.ELEMENT_NODE && current !== document.body) {
        let segment = current.tagName.toLowerCase();
        const className = typeof current.className === "string"
            ? current.className.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((name) => `.${CSS.escape(name)}`).join("")
            : "";

        if (className) {
            segment += className;
        }

        const siblings = current.parentElement
            ? Array.from(current.parentElement.children).filter((child) => child.tagName === current.tagName)
            : [];

        if (siblings.length > 1) {
            segment += `:nth-of-type(${siblings.indexOf(current) + 1})`;
        }

        path.unshift(segment);
        const selector = path.join(" > ");
        try {
            if (document.querySelector(selector) === node) {
                return selector;
            }
        } catch (error) {
            // Ignore invalid intermediate selectors.
        }
        current = current.parentElement;
    }

    return path.join(" > ") || null;
}

async function requestCandidateSelection(candidates, intent) {
    candidates.forEach((candidate, index) => {
        if (candidate.selector) {
            elementHighlighter.highlightElement(candidate.selector, 1200, index === 0 ? "Recommended" : `Option ${index + 1}`);
        }
    });

    return new Promise((resolve) => {
        feedbackCollector.showCandidates(
            candidates,
            {
                title: "Confirm Target",
                subtitle: `Navis needs confirmation for: ${intent.goal}`
            },
            (selectedCandidate) => {
                elementHighlighter.removeHighlight();
                resolve(selectedCandidate);
            }
        );
    });
}

async function executeSelectedAction(selected, intent) {
    const actionType = selected.action_type || intent.action_type || "click";
    isActionRunning = true;
    interruptDetector.startMonitoring(handleInterrupt);

    try {
        switch (actionType) {
            case "click":
                return await executeClick(selected.selector);
            case "highlight":
                return await executeHighlight(selected.selector, 3000, "Target");
            case "scroll_up":
                return await navigationController.scrollUp(500);
            case "scroll_down":
                return await navigationController.scrollDown(500);
            case "navigate_back":
                return await navigationController.goBack();
            case "navigate_forward":
                return await navigationController.goForward();
            default:
                return {
                    success: false,
                    action: actionType,
                    message: `Unsupported action type: ${actionType}`
                };
        }
    } finally {
        interruptDetector.stopMonitoring();
        isActionRunning = false;
    }
}

async function executeClick(selector) {
    if (!selector) {
        return { success: false, action: "click", message: "No selector provided" };
    }

    const element = document.querySelector(selector);
    if (!element) {
        return { success: false, action: "click", selector, message: "Element not found" };
    }

    element.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
    await wait(250);
    elementHighlighter.highlightElement(selector, 1000, "Clicking");
    await wait(350);
    element.click();
    return { success: true, action: "click", selector, message: "Element clicked" };
}

async function executeHighlight(selector, duration, label) {
    if (!selector) {
        return { success: false, action: "highlight", message: "No selector provided" };
    }
    const success = elementHighlighter.highlightElement(selector, duration, label);
    return {
        success,
        action: "highlight",
        selector,
        message: success ? "Element highlighted" : "Failed to highlight element"
    };
}

async function requestResultFeedback(userGoal, selected) {
    return new Promise((resolve) => {
        feedbackCollector.showFeedbackForm(selected, async (feedback) => {
            if (feedback) {
                await postFeedback(
                    userGoal,
                    getPageInfo(),
                    selected,
                    feedback.type === "correct_action" ? "success" : "user_override",
                    feedback.type
                );
            }
            resolve(feedback);
        });
    });
}

function shouldAskForFeedback(selected, result) {
    return Boolean(result.success && selected && selected.selector);
}

async function handleInterrupt(interruptData) {
    if (!isActionRunning) {
        return;
    }
    interruptDetector.stopMonitoring();
    isActionRunning = false;
    chrome.runtime.sendMessage({
        type: "navis_action_interrupted",
        interrupt: interruptData
    });
}

async function postFeedback(userGoal, pageContext, selected, outcome, notes) {
    if (!sessionId) {
        return;
    }
    try {
        await postJson("/feedback", {
            session_id: sessionId,
            user_goal: userGoal,
            page_context: pageContext,
            selected,
            outcome,
            notes
        });
    } catch (error) {
        console.error("[Navis] Failed to post feedback:", error);
    }
}

async function postJson(path, payload) {
    const response = await fetch(`${BACKEND_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const text = await response.text();
        throw new Error(`Backend request failed (${response.status}): ${text}`);
    }
    return response.json();
}

function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeNavis);
} else {
    initializeNavis();
}

console.log("[Navis] Content script loaded");
