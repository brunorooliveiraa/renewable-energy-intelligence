import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { existsSync } from "node:fs";
import {
  mkdtemp,
  readFile,
  rm,
  stat,
} from "node:fs/promises";
import { createServer } from "node:http";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

const PROJECT_ROOT = path.resolve(import.meta.dirname, "..");
const FRONTEND_ROOT = path.join(PROJECT_ROOT, "frontend");

assert.equal(
  typeof WebSocket,
  "function",
  "Node.js 22+ é obrigatório para o cliente nativo do Chrome DevTools Protocol.",
);

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function findChrome() {
  const configured = process.env.CHROME_BIN;
  const candidates = [
    configured,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ].filter(Boolean);
  const executable = candidates.find((candidate) => existsSync(candidate));
  assert.ok(
    executable,
    "Chrome/Chromium não encontrado. Defina CHROME_BIN com o executável do navegador.",
  );
  return executable;
}

function jsonResponse(response, status, payload) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  response.end(JSON.stringify(payload));
}

function overviewPayload(empty = false) {
  return {
    has_data: !empty,
    methodology: { revision_notice: "Dados sujeitos a revisão oficial." },
    summary: empty
      ? null
      : {
          total_intervalos: 48,
          intervalos_com_restricao: 8,
          taxa_intervalos_restricao_pct: 16.6667,
          empreendimentos_observados: 2,
          empreendimentos_com_restricao: 2,
          intervalos_elegiveis_geracao: 48,
          intervalos_elegiveis_referencia_final: 8,
          geracao_verificada_mwh: 120.5,
          geracao_referencia_final_mwh: 30.25,
          minutos_restricao_total: 240,
        },
  };
}

function timeseriesPayload() {
  return {
    has_data: true,
    items: [
      {
        periodo_referencia: "2025-01-01",
        total_intervalos: 24,
        intervalos_com_restricao: 3,
        taxa_intervalos_restricao_pct: 12.5,
        geracao_verificada_mwh: 55.25,
        geracao_referencia_final_mwh: 12.5,
        minutos_restricao_total: 90,
      },
      {
        periodo_referencia: "2025-01-02",
        total_intervalos: 24,
        intervalos_com_restricao: 5,
        taxa_intervalos_restricao_pct: 20.8333,
        geracao_verificada_mwh: 65.25,
        geracao_referencia_final_mwh: 17.75,
        minutos_restricao_total: 150,
      },
    ],
  };
}

function enterpriseItem(id, name) {
  return {
    ons_id: id,
    usina_nome: name,
    ceg: "-",
    tipo_identificador: "conjunto_sem_ceg",
    elegivel_enriquecimento_aneel: false,
    total_intervalos: 48,
    intervalos_com_restricao: 8,
    taxa_intervalos_restricao_pct: 16.6667,
    intervalos_elegiveis_geracao: 48,
    intervalos_elegiveis_referencia_final: 8,
    geracao_verificada_mwh: 120.5,
    geracao_referencia_final_mwh: 30.25,
    minutos_restricao_total: 240,
  };
}

function reasonsPayload() {
  const reason = (code, count) => ({
    restricao_razao_codigo: code,
    intervalos_com_restricao: count,
    participacao_restricoes_pct: count ? 100 : 0,
    empreendimentos_afetados: count ? 2 : 0,
    geracao_verificada_mwh: count ? 120.5 : null,
    geracao_referencia_final_mwh: count ? 30.25 : null,
    minutos_restricao_total: count ? 240 : null,
  });
  const origin = (code, count) => ({
    restricao_origem_codigo: code,
    intervalos_com_restricao: count,
    participacao_restricoes_pct: count ? 100 : 0,
    empreendimentos_afetados: count ? 2 : 0,
    geracao_verificada_mwh: count ? 120.5 : null,
    geracao_referencia_final_mwh: count ? 30.25 : null,
    minutos_restricao_total: count ? 240 : null,
  });
  return {
    has_data: true,
    by_reason: [reason("ENE", 8), reason("REL", 0), reason("CNF", 0), reason("PAR", 0)],
    by_origin: [origin("SIS", 8), origin("LOC", 0)],
    items: [
      {
        ...reason("ENE", 8),
        restricao_origem_codigo: "SIS",
        intervalos_elegiveis_geracao: 8,
        intervalos_elegiveis_referencia_final: 8,
      },
    ],
    top_descriptions: [
      {
        restricao_razao_codigo: "ENE",
        restricao_origem_codigo: "SIS",
        restricao_descricao: "Restrição energética sistêmica",
        intervalos_com_restricao: 8,
      },
    ],
  };
}

function qualityPayload() {
  return {
    has_data: true,
    last_loaded_at_utc: "2026-11-23T12:00:00+00:00",
    coverage: {
      total_intervalos: 48,
      elegivel_geracao_verificada: 48,
      taxa_cobertura_referencia_final_pct: 16.6667,
      sem_referencia_final: 40,
      taxa_cobertura_gnra_pct: 16.6667,
      elegivel_gnra: 8,
      empreendimentos_com_ceg: 1,
      conjuntos_sem_ceg: 1,
    },
    executions: [
      {
        estado_sigla: "CE",
        ano_referencia: 2025,
        mes_referencia: 1,
        arquivo_bruto_nome: "restricoes_2025_01.csv",
        arquivo_bruto_sha256: "a".repeat(64),
        linhas_entrada: 48,
        linhas_carregadas: 48,
        carregado_em_utc: "2026-11-23T12:00:00+00:00",
        metodologia_versao: "1.0",
      },
    ],
  };
}

async function createMockServer(requestLog) {
  const failedOnce = new Set();
  const server = createServer(async (request, response) => {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    requestLog.push(`${url.pathname}${url.search}`);

    if (url.pathname.startsWith("/api/")) {
      if (url.pathname === "/api/health") {
        jsonResponse(response, 200, { status: "ok", database_configured: true });
        return;
      }
      if (url.pathname === "/api/overview") {
        const onsId = url.searchParams.get("ons_id");
        if (onsId === "FAIL_ONCE" && !failedOnce.has(onsId)) {
          failedOnce.add(onsId);
          jsonResponse(response, 503, { detail: "Falha controlada para testar nova tentativa." });
          return;
        }
        jsonResponse(
          response,
          200,
          overviewPayload(url.searchParams.get("start_date") === "2026-01-01"),
        );
        return;
      }
      if (url.pathname === "/api/timeseries") {
        jsonResponse(response, 200, timeseriesPayload());
        return;
      }
      if (url.pathname === "/api/enterprises") {
        const offset = Number(url.searchParams.get("offset") ?? 0);
        const items = offset >= 20
          ? [enterpriseItem("CE_PAGE_2", "Conjunto Página 2")]
          : [
              enterpriseItem("CE_FILTER", "Conjunto Filtrado"),
              enterpriseItem("CE_SECOND", "Conjunto Secundário"),
            ];
        jsonResponse(response, 200, {
          has_data: true,
          pagination: { total: 21, limit: 20, offset },
          items,
        });
        return;
      }
      if (url.pathname === "/api/reasons") {
        jsonResponse(response, 200, reasonsPayload());
        return;
      }
      if (url.pathname === "/api/quality") {
        jsonResponse(response, 200, qualityPayload());
        return;
      }
      jsonResponse(response, 404, { detail: "Rota simulada não encontrada." });
      return;
    }

    const requested = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
    const filePath = path.resolve(FRONTEND_ROOT, requested);
    if (!filePath.startsWith(`${FRONTEND_ROOT}${path.sep}`) && filePath !== path.join(FRONTEND_ROOT, "index.html")) {
      response.writeHead(403);
      response.end("Forbidden");
      return;
    }
    try {
      const fileStat = await stat(filePath);
      if (!fileStat.isFile()) throw new Error("not a file");
      const extension = path.extname(filePath);
      const contentTypes = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".jpg": "image/jpeg",
      };
      response.writeHead(200, { "Content-Type": contentTypes[extension] ?? "application/octet-stream" });
      response.end(await readFile(filePath));
    } catch {
      response.writeHead(404);
      response.end("Not found");
    }
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  return server;
}

class CdpClient {
  constructor(socket) {
    this.socket = socket;
    this.nextId = 1;
    this.pending = new Map();
    socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(message.error.message));
      else resolve(message.result);
    });
  }

  static async connect(url) {
    const socket = new WebSocket(url);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    return new CdpClient(socket);
  }

  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  async evaluate(expression) {
    const result = await this.send("Runtime.evaluate", {
      expression,
      awaitPromise: true,
      returnByValue: true,
    });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description ?? "Falha ao avaliar JavaScript no navegador.");
    }
    return result.result.value;
  }

  close() {
    this.socket.close();
  }
}

async function waitForFile(filePath, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (existsSync(filePath)) return;
    await sleep(50);
  }
  throw new Error(`Tempo esgotado aguardando ${filePath}.`);
}

async function waitForPage(debugPort, timeoutMs = 15_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const targets = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((response) => response.json());
      const page = targets.find((target) => target.type === "page" && target.url.startsWith("http://127.0.0.1:"));
      if (page) return page;
    } catch {
      // O Chrome ainda está inicializando; a repetição possui prazo explícito.
    }
    await sleep(50);
  }
  throw new Error("Tempo esgotado aguardando a página do dashboard no Chrome.");
}

async function waitFor(client, expression, message, timeoutMs = 10_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await client.evaluate(expression)) return;
    await sleep(50);
  }
  throw new Error(message);
}

test("todos os botões da primeira tela e os fluxos funcionais críticos", async () => {
  const chromeExecutable = findChrome();
  const requestLog = [];
  const server = await createMockServer(requestLog);
  const address = server.address();
  assert.ok(address && typeof address === "object");
  const baseUrl = `http://127.0.0.1:${address.port}`;
  const profileDir = await mkdtemp(path.join(PROJECT_ROOT, ".e2e-chrome-"));
  const activePortFile = path.join(profileDir, "DevToolsActivePort");
  const chrome = spawn(
    chromeExecutable,
    [
      "--headless=new",
      "--disable-gpu",
      "--disable-breakpad",
      "--disable-crash-reporter",
      "--no-first-run",
      "--no-default-browser-check",
      "--remote-allow-origins=*",
      "--remote-debugging-port=0",
      `--user-data-dir=${profileDir}`,
      `${baseUrl}/`,
    ],
    { stdio: "ignore" },
  );
  let client;

  try {
    await waitForFile(activePortFile);
    const [debugPortText] = (await readFile(activePortFile, "utf8")).trim().split(/\r?\n/);
    const page = await waitForPage(Number(debugPortText));
    client = await CdpClient.connect(page.webSocketDebuggerUrl);
    await client.send("Runtime.enable");
    await waitFor(
      client,
      "document.readyState === 'complete' && document.querySelector('#overview-top-tbody tr[data-open-enterprise]') !== null",
      "A tela inicial não concluiu o carregamento.",
    );

    await client.evaluate(`(() => {
      window.__clickedButtons = [];
      window.__downloads = [];
      window.__buttonKey = (button) => button.id
        || (button.dataset.tab ? 'tab:' + button.dataset.tab : '')
        || (button.dataset.granularity ? 'granularity:' + button.dataset.granularity : '')
        || (button.dataset.gotoTab ? 'goto:' + button.dataset.gotoTab : '')
        || (button.dataset.action ? 'action:' + button.dataset.action : '')
        || button.textContent.trim();
      document.addEventListener('click', (event) => {
        const button = event.target.closest('button');
        if (button) window.__clickedButtons.push(window.__buttonKey(button));
      }, true);
      HTMLAnchorElement.prototype.click = function () {
        if (this.download) window.__downloads.push(this.download);
      };
      return true;
    })()`);

    const click = async (selector) => {
      const clicked = await client.evaluate(`(() => {
        const element = document.querySelector(${JSON.stringify(selector)});
        if (!element || element.hidden || element.disabled) return false;
        element.click();
        return true;
      })()`);
      assert.equal(clicked, true, `Botão indisponível para clique: ${selector}`);
      await sleep(80);
    };
    const setValue = (selector, value) => client.evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      element.value = ${JSON.stringify(value)};
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`);

    await click('[data-granularity="monthly"]');
    await waitFor(client, "document.querySelector('[data-granularity=\"monthly\"]').getAttribute('aria-pressed') === 'true'", "Granularidade mensal não foi ativada.");
    await click('[data-granularity="daily"]');
    await click("#btn-export-active");
    assert.ok((await client.evaluate("window.__downloads")).at(-1).startsWith("serie_temporal_"));

    await click('[data-goto-tab="enterprises"]');
    await waitFor(client, "document.querySelector('#panel-enterprises:not([hidden]) #enterprises-tbody tr[data-ons-id]') !== null", "A aba de empreendimentos não carregou.");
    await click("#btn-export-enterprises");
    await click("#btn-ent-next");
    await waitFor(client, "document.querySelector('#enterprises-pagination-info').textContent.includes('21–21')", "A próxima página não foi carregada.");
    await click("#btn-ent-prev");
    await waitFor(client, "document.querySelector('#enterprises-pagination-info').textContent.includes('1–2')", "A página anterior não foi restaurada.");
    await client.evaluate("document.querySelector('#enterprises-tbody tr[data-ons-id]').click()");
    await waitFor(client, "!document.querySelector('#enterprise-detail-section').hidden", "O detalhe do empreendimento não abriu.");
    await click("#btn-filter-by-enterprise");

    await click("#tab-btn-enterprises");
    await waitFor(client, "document.querySelector('#enterprises-tbody tr[data-ons-id]') !== null", "Empreendimentos não recarregaram.");
    await client.evaluate("document.querySelector('#enterprises-tbody tr[data-ons-id]').click()");
    await waitFor(client, "!document.querySelector('#enterprise-detail-section').hidden", "O detalhe não reabriu.");
    await click("#btn-close-enterprise-detail");

    await click("#tab-btn-reasons");
    await waitFor(client, "document.querySelector('#reasons-tbody tr') !== null", "A aba de motivos não carregou.");
    await click("#btn-export-reasons");

    await click("#tab-btn-quality");
    await waitFor(client, "document.querySelector('#executions-tbody tr') !== null", "A aba de qualidade não carregou.");
    await click("#btn-export-active");
    assert.equal((await client.evaluate("window.__downloads")).at(-1), "qualidade_execucoes_CE.csv");

    await click("#tab-btn-overview");
    await click('[data-goto-tab="reasons"]');
    await click("#tab-btn-overview");

    await setValue("#filter-ons-id", "CE_FILTER");
    await click("#btn-apply-filters");
    await waitFor(client, "document.querySelector('#header-period-chip').textContent.includes('CE_FILTER')", "O filtro ons_id não foi aplicado.");
    assert.ok(
      requestLog.some((url) => url.startsWith("/api/enterprises?") && url.includes("ons_id=CE_FILTER")),
      "A chamada do ranking não recebeu o filtro ons_id.",
    );
    await click("#btn-reset-filters");

    await setValue("#filter-ons-id", "FAIL_ONCE");
    await click("#btn-apply-filters");
    await waitFor(client, "!document.querySelector('#global-error-banner').hidden", "O estado de erro não apareceu.");
    await click("#btn-retry-global");
    await waitFor(client, "document.querySelector('#global-error-banner').hidden", "A nova tentativa não recuperou a tela.");

    await setValue("#filter-ons-id", "");
    await setValue("#filter-start-date", "2026-01-01");
    await setValue("#filter-end-date", "2026-01-31");
    await click("#btn-apply-filters");
    await waitFor(client, "!document.querySelector('#overview-empty').hidden", "O estado vazio não apareceu.");
    await click('[data-action="reset-filters"]');

    const coverage = await client.evaluate(`(() => {
      const all = Array.from(document.querySelectorAll('button')).map(window.__buttonKey);
      return { all, clicked: Array.from(new Set(window.__clickedButtons)) };
    })()`);
    const missing = coverage.all.filter((key) => !coverage.clicked.includes(key));
    assert.deepEqual(missing, [], `Botões sem cobertura E2E: ${missing.join(", ")}`);
    assert.equal(coverage.all.length, 19, "A quantidade de botões mudou; revise a cobertura E2E.");
  } finally {
    if (client) {
      try {
        await client.send("Browser.close");
      } catch {
        // O processo pode ter encerrado entre a última asserção e a limpeza.
      }
      client.close();
    }
    if (chrome.exitCode === null) {
      chrome.kill();
      await Promise.race([once(chrome, "exit"), sleep(5_000)]);
    }
    await new Promise((resolve) => server.close(resolve));
    await rm(profileDir, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
  }
});
