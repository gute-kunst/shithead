export function renderLandingTopbarView() {
  return `
    <div class="game-topbar">
      <div class="game-topbar-title">
        <strong class="game-topbar-name">Shithead</strong>
        <span class="game-topbar-eyebrow">Private Mobile Alpha</span>
      </div>
    </div>
  `;
}

export function renderLandingBucketView({
  bucket,
  expanded,
  landingInviteCode,
  escapeHtml,
}) {
  const isCreate = bucket === "create";
  const title = isCreate ? "Create table" : "Join a table";
  const copy = isCreate
    ? "Start a private lobby and get an invite code for the other players."
    : "Enter the invite code and your display name to claim a seat.";
  const buttonLabel = isCreate ? "Create game" : "Join game";
  const formMarkup = isCreate
    ? `
      <form class="stack" data-mode="create">
        <div class="field">
          <label for="create-name">Display name</label>
          <input id="create-name" name="display_name" maxlength="24" required placeholder="your-name" />
        </div>
        <button class="button accent" type="submit">${buttonLabel}</button>
      </form>
    `
    : `
      <form class="stack" data-mode="join">
        <div class="field">
          <label for="join-code">Invite code</label>
          <input id="join-code" name="invite_code" maxlength="6" required placeholder="AB12CD" value="${escapeHtml(landingInviteCode)}" />
        </div>
        <div class="field">
          <label for="join-name">Display name</label>
          <input id="join-name" name="display_name" maxlength="24" required placeholder="your-name" />
        </div>
        <button class="button" type="submit">${buttonLabel}</button>
      </form>
    `;

  return `
    <article class="landing-table-card ${expanded ? "landing-table-card-expanded" : "landing-table-card-collapsed"} stack">
      <button
        class="landing-bucket-toggle"
        type="button"
        data-landing-bucket="${bucket}"
        aria-expanded="${expanded ? "true" : "false"}"
      >
        <span class="landing-bucket-copy">
          <strong>${title}</strong>
        </span>
        <span class="landing-bucket-icon" aria-hidden="true">${expanded ? "-" : "+"}</span>
      </button>
      <div class="landing-bucket-panel" aria-hidden="${expanded ? "false" : "true"}">
        <div class="landing-bucket-panel-inner stack">
          <p class="muted">${copy}</p>
          ${formMarkup}
        </div>
      </div>
    </article>
  `;
}

export function renderLandingView({
  landingJoinFirst,
  landingOpenBucket,
  landingInviteCode,
  showSavedSessionCard,
  restoringSession,
  inviteCode,
  displayName,
  error,
  rulesMenuHtml,
  escapeHtml,
}) {
  const landingBuckets = landingJoinFirst
    ? ["join", "create"]
    : ["create", "join"];

  const renderedBuckets = landingBuckets
    .map((bucket) =>
      renderLandingBucketView({
        bucket,
        expanded: landingOpenBucket === bucket,
        landingInviteCode,
        escapeHtml,
      }),
    )
    .join("");

  return `
    ${renderLandingTopbarView()}
    <section class="game-screen landing-screen">
      <section class="panel table-stage landing-table-stage">
        <div class="table-map landing-table-map">
          <div class="table-surface"></div>
          <div class="landing-table-content">
            <div class="landing-table-banner-row">
              <section class="landing-table-banner landing-alpha-banner">
                <strong>Alpha notice</strong>
                <p>Switching tabs or apps is okay for a while. Live games can still reset after a deploy, restart, or a long period of inactivity.</p>
              </section>
            </div>
            <div class="landing-form-row">
              ${renderedBuckets}
            </div>
            ${
              showSavedSessionCard
                ? `
              <div class="landing-table-banner-row landing-table-banner-row-bottom">
                <section class="landing-table-banner landing-table-resume stack">
                  <div>
                    <strong>${restoringSession ? "Restoring your game" : "Resume saved game"}</strong>
                    <p class="muted">
                      ${
                        restoringSession
                          ? "Reclaiming your seat and reconnecting to live updates."
                          : "A saved game was found on this device. You can restore it or forget it."
                      }
                    </p>
                  </div>
                  <div class="status-strip">
                    <span class="status-chip">Invite ${escapeHtml(inviteCode)}</span>
                    ${displayName ? `<span class="status-chip">${escapeHtml(displayName)}</span>` : ""}
                  </div>
                  ${error ? `<div class="dock-error">${escapeHtml(error)}</div>` : ""}
                  ${
                    !restoringSession
                      ? `
                    <div class="secondary-action-row">
                      <button class="button accent" id="restore-session">Restore saved session</button>
                      <button class="button secondary" id="forget-session">Forget saved session</button>
                    </div>
                  `
                      : ""
                  }
                </section>
              </div>
            `
                : error
                  ? `
              <div class="landing-table-banner-row landing-table-banner-row-bottom">
                <section class="landing-table-banner landing-table-error">
                  <strong>${escapeHtml(error)}</strong>
                </section>
              </div>
            `
                  : ""
            }
          </div>
          <button class="table-help-trigger" id="open-rules-menu" type="button" aria-label="Open rules" title="Rules">?</button>
          ${rulesMenuHtml}
        </div>
      </section>
    </section>
  `;
}

export function renderGameTopbarView({
  showCompactBrand,
  wsReady,
  leaveArmed,
}) {
  const leaveButtonLabel = "Leave";
  const leaveButtonTitle = leaveArmed ? "Click again to leave" : "Leave";

  return `
    <div class="game-topbar ${showCompactBrand ? "" : "actions-only"}">
      ${
        showCompactBrand
          ? `
        <div class="game-topbar-title">
          <strong class="game-topbar-name">Shithead</strong>
          <span class="game-topbar-eyebrow">Private Mobile Alpha</span>
        </div>
      `
          : ""
      }
      <div class="game-topbar-actions">
        <span
          class="connection-indicator ${wsReady ? "connected" : "reconnecting"}"
          title="${wsReady ? "Live sync connected" : "Reconnecting"}"
          aria-label="${wsReady ? "Live sync connected" : "Reconnecting"}"
        ></span>
        <button
          class="button secondary button-inline ${leaveArmed ? "armed-leave" : ""}"
          id="leave-game-header"
          title="${leaveButtonTitle}"
          aria-label="${leaveButtonTitle}"
        >${leaveButtonLabel}</button>
      </div>
    </div>
  `;
}

export function renderAppView({
  gameTopbarHtml,
  gameScreenClasses,
  tableHtml,
  actionsHtml,
  motionLayerHtml,
  globalErrorHtml,
}) {
  return `
    ${gameTopbarHtml}
    <section class="${gameScreenClasses}">
      ${tableHtml}
      ${actionsHtml}
      ${motionLayerHtml}
    </section>
    ${globalErrorHtml}
  `;
}
