const copyButton = document.getElementById("copy-link");
const invitationLink = document.getElementById("invitation-link");
const copyStatus = document.getElementById("copy-status");
let resetCopyState;

copyButton.addEventListener("click", async () => {
  clearTimeout(resetCopyState);
  copyButton.disabled = true;
  try {
    await navigator.clipboard.writeText(invitationLink.value);
    copyButton.querySelector("span").textContent = "Copied!";
    copyButton.classList.add("is-copied");
    copyStatus.textContent = "Link copied to your clipboard.";
    resetCopyState = setTimeout(() => {
      copyButton.querySelector("span").textContent = "Copy link";
      copyButton.classList.remove("is-copied");
      copyStatus.textContent = "";
    }, 4000);
  } catch {
    copyButton.querySelector("span").textContent = "Copy link";
    copyButton.classList.remove("is-copied");
    invitationLink.focus();
    invitationLink.select();
    copyStatus.textContent = "Couldn’t access your clipboard. The link is selected; use your device’s Copy command.";
  } finally {
    copyButton.disabled = false;
  }
});
