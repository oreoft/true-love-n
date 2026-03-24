import type {
  ChannelAccountSnapshot,
  PluginRuntime,
} from "openclaw/plugin-sdk";

import { getUpdates, sendMessage } from "../api/api.js";
import { MessageItemType, MessageState, MessageType } from "../api/types.js";
import { WeixinConfigManager } from "../api/config-cache.js";
import {
  SESSION_EXPIRED_ERRCODE,
  getRemainingPauseMs,
  pauseSession,
} from "../api/session-guard.js";
import { loadWeixinAccount } from "../auth/accounts.js";
import { processOneMessage } from "../messaging/process-message.js";
import { waitForWeixinRuntime } from "../runtime.js";
import {
  getSyncBufFilePath,
  loadGetUpdatesBuf,
  saveGetUpdatesBuf,
} from "../storage/sync-buf.js";
import { logger } from "../util/logger.js";
import type { Logger } from "../util/logger.js";
import { redactBody } from "../util/redact.js";

const DEFAULT_LONG_POLL_TIMEOUT_MS = 35_000;
// Warn user after this many consecutive failures (before the full backoff threshold)
const INSTABILITY_WARNING_THRESHOLD = 3;
// Full backoff after this many consecutive failures
const MAX_CONSECUTIVE_FAILURES = 5;
const BACKOFF_DELAY_MS = 30_000;
const RETRY_DELAY_MS = 2_000;

export type MonitorWeixinOpts = {
  baseUrl: string;
  cdnBaseUrl: string;
  token?: string;
  accountId: string;
  /** When non-empty, only messages whose from_user_id is in this list are processed. */
  allowFrom?: string[];
  config: import("openclaw/plugin-sdk/core").OpenClawConfig;
  runtime?: { log?: (msg: string) => void; error?: (msg: string) => void };
  abortSignal?: AbortSignal;
  longPollTimeoutMs?: number;
  /** Gateway status callback — called on each successful poll and inbound message. */
  setStatus?: (next: ChannelAccountSnapshot) => void;
};

/**
 * Long-poll loop: getUpdates -> normalize -> recordInboundSession -> dispatchReplyFromConfig.
 * Runs until abort.
 */
export async function monitorWeixinProvider(
  opts: MonitorWeixinOpts,
): Promise<void> {
  const {
    baseUrl,
    cdnBaseUrl,
    token,
    accountId,
    config,
    abortSignal,
    longPollTimeoutMs,
    setStatus,
  } = opts;
  const log = opts.runtime?.log ?? (() => {});
  const errLog = opts.runtime?.error ?? ((m: string) => log(m));
  const aLog: Logger = logger.withAccount(accountId);

  aLog.info(`waiting for Weixin runtime...`);
  let channelRuntime: PluginRuntime["channel"];
  try {
    const pluginRuntime = await waitForWeixinRuntime();
    channelRuntime = pluginRuntime.channel;
    aLog.info(
      `Weixin runtime acquired, channelRuntime type: ${typeof channelRuntime}`,
    );
  } catch (err) {
    aLog.error(`waitForWeixinRuntime() failed: ${String(err)}`);
    throw err;
  }

  log(`weixin monitor started (${baseUrl}, account=${accountId})`);
  aLog.info(
    `Monitor started: baseUrl=${baseUrl} timeoutMs=${longPollTimeoutMs ?? DEFAULT_LONG_POLL_TIMEOUT_MS}`,
  );

  const syncFilePath = getSyncBufFilePath(accountId);
  aLog.debug(`syncFilePath: ${syncFilePath}`);

  const previousGetUpdatesBuf = loadGetUpdatesBuf(syncFilePath);
  let getUpdatesBuf = previousGetUpdatesBuf ?? "";

  if (previousGetUpdatesBuf) {
    log(
      `[weixin] resuming from previous sync buf (${getUpdatesBuf.length} bytes)`,
    );
    aLog.debug(
      `Using previous get_updates_buf (${getUpdatesBuf.length} bytes)`,
    );
  } else {
    log(`[weixin] no previous sync buf, starting fresh`);
    aLog.info(`No previous get_updates_buf found, starting fresh`);
  }

  const configManager = new WeixinConfigManager({ baseUrl, token }, log);

  let nextTimeoutMs = longPollTimeoutMs ?? DEFAULT_LONG_POLL_TIMEOUT_MS;
  let consecutiveFailures = 0;
  let lastInstabilityWarningAt = 0;
  let hasSentInstabilityWarning = false;

  const accountData = loadWeixinAccount(accountId);
  const ownerUserId = accountData?.userId;

  while (!abortSignal?.aborted) {
    try {
      aLog.debug(
        `getUpdates: get_updates_buf=${getUpdatesBuf.substring(0, 50)}..., timeoutMs=${nextTimeoutMs}`,
      );
      const resp = await getUpdates({
        baseUrl,
        token,
        get_updates_buf: getUpdatesBuf,
        timeoutMs: nextTimeoutMs,
      });
      aLog.debug(
        `getUpdates response: ret=${resp.ret}, msgs=${resp.msgs?.length ?? 0}, get_updates_buf_length=${resp.get_updates_buf?.length ?? 0}`,
      );

      if (
        resp.longpolling_timeout_ms != null &&
        resp.longpolling_timeout_ms > 0
      ) {
        nextTimeoutMs = resp.longpolling_timeout_ms;
        aLog.debug(`Updated next poll timeout: ${nextTimeoutMs}ms`);
      }
      const isApiError =
        (resp.ret !== undefined && resp.ret !== 0) ||
        (resp.errcode !== undefined && resp.errcode !== 0);
      if (isApiError) {
        const isSessionExpired =
          resp.errcode === SESSION_EXPIRED_ERRCODE ||
          resp.ret === SESSION_EXPIRED_ERRCODE;

        if (isSessionExpired) {
          pauseSession(accountId);
          const pauseMs = getRemainingPauseMs(accountId);
          errLog(
            `weixin getUpdates: session expired (errcode ${SESSION_EXPIRED_ERRCODE}), pausing bot for ${Math.ceil(pauseMs / 60_000)} min`,
          );
          aLog.error(
            `getUpdates: session expired (errcode=${resp.errcode} ret=${resp.ret}), pausing all requests for ${Math.ceil(pauseMs / 60_000)} min`,
          );
          setStatus?.({
            accountId,
            lastError: `Session Expired (${resp.errcode ?? resp.ret})`,
            running: false,
          });
          consecutiveFailures = 0;
          await sleep(pauseMs, abortSignal);
          continue;
        }

        consecutiveFailures += 1;

        // Stability Notification: Instability Warning
        if (
          consecutiveFailures === INSTABILITY_WARNING_THRESHOLD &&
          ownerUserId &&
          token &&
          Date.now() - lastInstabilityWarningAt > 3600_000
        ) {
          lastInstabilityWarningAt = Date.now();
          hasSentInstabilityWarning = true;
          const warningText = `呜哇… 网络信号好像在跟人家躲猫猫… o(╥﹏╥)o\n\n**真爱粉** 检测到现在的连接不太稳定，人家正在拼命重连中！如果我长时间没理您，可能需要大佬检查一下网络，或者看看是否要重新把我召唤回来（重新扫码）哦。`;
          void sendMessage({
            baseUrl,
            token,
            body: {
              msg: {
                to_user_id: ownerUserId,
                message_type: MessageType.BOT,
                message_state: MessageState.FINISH,
                item_list: [
                  { type: MessageItemType.TEXT, text_item: { text: warningText } },
                ],
              },
            },
          }).catch((e) =>
            aLog.warn(`Failed to send instability warning: ${String(e)}`),
          );
        }

        errLog(
          `weixin getUpdates failed: ret=${resp.ret} errcode=${resp.errcode} errmsg=${resp.errmsg ?? ""} (${consecutiveFailures}/${MAX_CONSECUTIVE_FAILURES})`,
        );
        aLog.error(
          `getUpdates failed: ret=${resp.ret} errcode=${resp.errcode} errmsg=${resp.errmsg} response=${redactBody(JSON.stringify(resp))}`,
        );
        setStatus?.({
          accountId,
          lastError: `API Error: ${resp.errmsg || resp.errcode || resp.ret}`,
        });
        if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
          errLog(
            `weixin getUpdates: ${MAX_CONSECUTIVE_FAILURES} consecutive failures, backing off 30s`,
          );
          aLog.error(
            `getUpdates: ${MAX_CONSECUTIVE_FAILURES} consecutive failures, backing off 30s`,
          );
          // Do NOT reset consecutiveFailures here — keep the count so the
          // recovery message fires correctly once the connection comes back.
          await sleep(BACKOFF_DELAY_MS, abortSignal);
        } else {
          await sleep(RETRY_DELAY_MS, abortSignal);
        }
        continue;
      }

      // Stability Notification: Recovery Message — fires once when connection recovers
      // after we had warned the user about instability.
      if (hasSentInstabilityWarning && ownerUserId && token) {
        hasSentInstabilityWarning = false;
        const recoveryText = `连接恢复啦！欧耶~ ☆\n\n让大佬久等了，**真爱粉** 已经重新连接到主世界，服务继续满血运转中！(๑•̀ㅂ•́)و✧`;
        void sendMessage({
          baseUrl,
          token,
          body: {
            msg: {
              to_user_id: ownerUserId,
              message_type: MessageType.BOT,
              message_state: MessageState.FINISH,
              item_list: [
                { type: MessageItemType.TEXT, text_item: { text: recoveryText } },
              ],
            },
          },
        }).catch((e) =>
          aLog.warn(`Failed to send recovery message: ${String(e)}`),
        );
      }

      consecutiveFailures = 0;
      setStatus?.({ accountId, lastEventAt: Date.now(), lastError: null });
      if (resp.get_updates_buf != null && resp.get_updates_buf !== "") {
        saveGetUpdatesBuf(syncFilePath, resp.get_updates_buf);
        getUpdatesBuf = resp.get_updates_buf;
        aLog.debug(`Saved new get_updates_buf (${getUpdatesBuf.length} bytes)`);
      }
      const list = resp.msgs ?? [];
      for (const full of list) {
        aLog.info(
          `inbound message: from=${full.from_user_id} types=${full.item_list?.map((i) => i.type).join(",") ?? "none"}`,
        );

        const now = Date.now();
        setStatus?.({ accountId, lastEventAt: now, lastInboundAt: now });

        // allowFrom filtering is delegated to processOneMessage via the framework
        // authorization pipeline (resolveSenderCommandAuthorizationWithRuntime).

        const fromUserId = full.from_user_id ?? "";
        const cachedConfig = await configManager.getForUser(
          fromUserId,
          full.context_token,
        );

        await processOneMessage(full, {
          accountId,
          config,
          channelRuntime,
          baseUrl,
          cdnBaseUrl,
          token,
          typingTicket: cachedConfig.typingTicket,
          log: opts.runtime?.log ?? (() => {}),
          errLog,
        });
      }
    } catch (err) {
      if (abortSignal?.aborted) {
        aLog.info(`Monitor stopped (aborted)`);
        return;
      }
      consecutiveFailures += 1;
      errLog(
        `weixin getUpdates error (${consecutiveFailures}/${MAX_CONSECUTIVE_FAILURES}): ${String(err)}`,
      );
      aLog.error(
        `getUpdates error: ${String(err)}, stack=${(err as Error).stack}`,
      );
      if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
        errLog(
          `weixin getUpdates: ${MAX_CONSECUTIVE_FAILURES} consecutive failures, backing off 30s`,
        );
        aLog.error(
          `getUpdates: ${MAX_CONSECUTIVE_FAILURES} consecutive failures, backing off 30s`,
        );
        consecutiveFailures = 0;
        await sleep(30_000, abortSignal);
      } else {
        await sleep(2000, abortSignal);
      }
    }
  }
  aLog.info(`Monitor ended`);
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(new Error("aborted"));
      },
      { once: true },
    );
  });
}
