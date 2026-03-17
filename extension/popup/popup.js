const goalInput = document.getElementById("goal-input");
const runButton = document.getElementById("run-goal");
const statusNode = document.getElementById("status");

runButton.addEventListener("click", async () => {
    const userGoal = goalInput.value.trim();
    if (!userGoal) {
        setStatus("Enter a goal first.");
        return;
    }

    setBusy(true, "Running...");

    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab?.id) {
            throw new Error("No active tab found");
        }

        const response = await chrome.tabs.sendMessage(tab.id, {
            type: "navis_run_goal",
            userGoal
        });

        if (!response?.success) {
            throw new Error(response?.error || "Unknown error");
        }

        const result = response.result;
        if (result.cancelled) {
            setStatus("Cancelled.");
        } else if (result.ok) {
            const actionType = result.result?.action || result.selected?.action_type || result.intent?.action_type || "action";
            const text = result.selected?.text || result.selected?.selector || result.intent?.target || "";
            setStatus(`Done: ${actionType}${text ? `\nTarget: ${text}` : ""}`);
        } else {
            setStatus(`Failed: ${result.message || "No action executed"}`);
        }
    } catch (error) {
        console.error("[Navis Popup] Run failed:", error);
        setStatus(`Error: ${error.message}`);
    } finally {
        setBusy(false);
    }
});

function setBusy(isBusy, message = "") {
    runButton.disabled = isBusy;
    runButton.textContent = isBusy ? "Running..." : "Run";
    if (message) {
        setStatus(message);
    }
}

function setStatus(message) {
    statusNode.textContent = message;
}
