import { expect, test } from "@playwright/test";

const dashboard = {
  workspaces: [{ id: "workspace-1", name: "Research", created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
  collections: [{ id: "collection-1", workspace_id: "workspace-1", name: "Product", document_count: 1 }],
  recent_documents: [
    {
      id: "doc-1",
      workspace_id: "workspace-1",
      title: "MongoDB Atlas Notes",
      source_type: "note",
      analysis_status: "complete",
      content: "Atlas can host MongoDB for production knowledge bases.",
      summary: "Atlas is a managed MongoDB option.",
      key_points: ["Managed MongoDB"],
      action_items: ["Configure MONGO_URI"],
      collection_ids: ["collection-1"],
      tags: ["mongodb", "atlas"],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ],
  insights: [
    {
      document_id: "doc-1",
      title: "MongoDB Atlas Notes",
      summary: "Atlas is a managed MongoDB option.",
      key_points: ["Managed MongoDB"],
      action_items: ["Configure MONGO_URI"]
    }
  ],
  activity: [{ id: "activity-1", action: "created", message: "Created note MongoDB Atlas Notes", created_at: new Date().toISOString() }]
};

const ragFeedback = {
  items: [
    {
      id: "feedback-1",
      user_id: "user-1",
      workspace_ids: ["workspace-1"],
      query: "Can I use Atlas?",
      answer: "Use MongoDB Atlas by setting MONGO_URI to your cluster connection string.",
      rating: "not_helpful",
      comment: null,
      citations: [
        {
          document_id: "doc-1",
          workspace_id: "workspace-1",
          document_title: "MongoDB Atlas Notes",
          chunk_index: 0,
          text: "Atlas can host MongoDB for production knowledge bases."
        }
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ],
  total: 1,
  limit: 10,
  offset: 0
};

const activityPage = {
  items: [
    {
      id: "activity-1",
      workspace_id: "workspace-1",
      actor_id: "user-1",
      action: "created",
      entity_type: "document",
      entity_id: "doc-1",
      message: "Created note MongoDB Atlas Notes",
      created_at: new Date().toISOString()
    }
  ],
  total: 1,
  limit: 50,
  offset: 0
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(({ dashboard, ragFeedback, activityPage }) => {
    localStorage.setItem("kbm_token", "test-token");
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const json = (body: unknown) =>
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "content-type": "application/json" }
        });
      if (url.endsWith("/health")) return json({ status: "ok" });
      if (url.endsWith("/ready")) return json({ status: "ready" });
      if (url.endsWith("/safety")) {
        return json({
          zero_cost_mode: true,
          ai_provider: "local",
          embedding_provider: "fastembed",
          openai_key_configured: false,
          paid_ai_blocked: false,
          paid_embeddings_blocked: false,
          billing_risk: false
        });
      }
      if (url.endsWith("/metrics.json")) {
        return json({
          uptime_seconds: 125,
          total_requests: 42,
          in_flight: 1,
          average_latency_ms: 14.5,
          status_counts: { "2xx": 42 },
          method_counts: { GET: 30, POST: 12 },
          path_counts: { "/api/v1/dashboard": 8 },
          recent_errors: []
        });
      }
      if (url.includes("/api/v1/dashboard/search")) return json({ items: dashboard.recent_documents, limit: 25, offset: 0 });
      if (url.includes("/api/v1/dashboard")) return json(dashboard);
      if (url.includes("/api/v1/activity")) return json(activityPage);
      if (url.includes("/api/v1/auth/password-reset/request")) {
        return json({ message: "If the account exists, a password reset token has been created.", reset_token: "reset-token-1234567890" });
      }
      if (url.includes("/api/v1/auth/password-reset/confirm")) return json({ message: "Password has been reset." });
      if (url.endsWith("/api/v1/workspaces")) return json(dashboard.workspaces);
      if (url.includes("/api/v1/workspaces/workspace-1/members")) {
        return json([{ id: "member-1", workspace_id: "workspace-1", user_id: "user-1", email: "owner@example.com", name: "Owner", role: "owner" }]);
      }
      if (url.includes("/api/v1/workspaces/workspace-1/documents")) {
        return json({ items: dashboard.recent_documents, total: 1, limit: 25, offset: 0 });
      }
      if (url.includes("/api/v1/rag/query/stream")) {
        const body = [
          'event: status\ndata: {"message":"retrieving"}\n\n',
          'event: citations\ndata: {"citations":[{"document_id":"doc-1","workspace_id":"workspace-1","document_title":"MongoDB Atlas Notes","chunk_index":0,"text":"Atlas can host MongoDB for production knowledge bases."}]}\n\n',
          'event: token\ndata: {"text":"Use MongoDB Atlas by setting MONGO_URI "}\n\n',
          'event: token\ndata: {"text":"to your cluster connection string."}\n\n',
          'event: done\ndata: {"answer":"Use MongoDB Atlas by setting MONGO_URI to your cluster connection string."}\n\n'
        ].join("");
        return new Response(body, { status: 200, headers: { "content-type": "text/event-stream" } });
      }
      if (url.includes("/api/v1/rag/query")) {
        return json({ answer: "Use MongoDB Atlas by setting MONGO_URI to your cluster connection string.", citations: [] });
      }
      if (url.includes("/api/v1/rag/feedback") && init?.method === "POST") return json({ id: "feedback-1", rating: "helpful" });
      if (url.includes("/api/v1/rag/feedback")) return json(ragFeedback);
      return originalFetch(input, init);
    };
  }, { dashboard, ragFeedback, activityPage });
  await page.route("**/api/v1/**", (route) => {
    const url = route.request().url();
    const headers = {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "authorization, content-type",
      "access-control-allow-methods": "GET, POST, PATCH, DELETE, OPTIONS"
    };
    if (route.request().method() === "OPTIONS") {
      return route.fulfill({ status: 204, headers });
    }
    if (url.includes("/dashboard/search")) {
      return route.fulfill({ headers, json: { items: dashboard.recent_documents, limit: 25, offset: 0 } });
    }
    if (url.endsWith("/dashboard")) {
      return route.fulfill({ headers, json: dashboard });
    }
    if (url.includes("/activity")) {
      return route.fulfill({ headers, json: activityPage });
    }
    if (url.endsWith("/auth/password-reset/request")) {
      return route.fulfill({
        headers,
        json: { message: "If the account exists, a password reset token has been created.", reset_token: "reset-token-1234567890" }
      });
    }
    if (url.endsWith("/auth/password-reset/confirm")) {
      return route.fulfill({ headers, json: { message: "Password has been reset." } });
    }
    if (url.endsWith("/workspaces")) {
      return route.fulfill({ headers, json: dashboard.workspaces });
    }
    if (url.includes("/workspaces/workspace-1/members")) {
      return route.fulfill({ headers, json: [{ id: "member-1", workspace_id: "workspace-1", user_id: "user-1", email: "owner@example.com", name: "Owner", role: "owner" }] });
    }
    if (url.includes("/workspaces/workspace-1/documents")) {
      return route.fulfill({ headers, json: { items: dashboard.recent_documents, total: 1, limit: 25, offset: 0 } });
    }
    if (url.endsWith("/rag/query/stream")) {
      const body = [
        'event: status\ndata: {"message":"retrieving"}\n\n',
        'event: citations\ndata: {"citations":[{"document_id":"doc-1","workspace_id":"workspace-1","document_title":"MongoDB Atlas Notes","chunk_index":0,"text":"Atlas can host MongoDB for production knowledge bases."}]}\n\n',
        'event: token\ndata: {"text":"Use MongoDB Atlas by setting MONGO_URI "}\n\n',
        'event: token\ndata: {"text":"to your cluster connection string."}\n\n',
        'event: done\ndata: {"answer":"Use MongoDB Atlas by setting MONGO_URI to your cluster connection string."}\n\n'
      ].join("");
      return route.fulfill({ headers: { ...headers, "content-type": "text/event-stream" }, body });
    }
    if (url.endsWith("/rag/query")) {
      return route.fulfill({
        headers,
        json: {
        answer: "Use MongoDB Atlas by setting MONGO_URI to your cluster connection string.",
        citations: [
          {
            document_id: "doc-1",
            document_title: "MongoDB Atlas Notes",
            chunk_index: 0,
            text: "Atlas can host MongoDB for production knowledge bases."
          }
        ]
      }
      });
    }
    if (url.endsWith("/rag/feedback") && route.request().method() === "POST") {
      return route.fulfill({ status: 201, headers, json: { id: "feedback-1", rating: "helpful" } });
    }
    if (url.includes("/rag/feedback")) {
      return route.fulfill({ headers, json: ragFeedback });
    }
    return route.fulfill({ status: 404, headers, json: { detail: "Not mocked" } });
  });
});

test("system status page shows operational safety and metrics", async ({ page }) => {
  await page.goto("/system");

  await expect(page.getByRole("heading", { name: "System status" })).toBeVisible();
  await expect(page.getByText("API ready")).toBeVisible();
  await expect(page.getByText("Zero-cost safe")).toBeVisible();
  await expect(page.getByText("No OpenAI key")).toBeVisible();
  await expect(page.getByText("42")).toBeVisible();
  await expect(page.getByText("No recent 500-level errors.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "RAG feedback review" })).toBeVisible();
  await expect(page.getByText("Can I use Atlas?")).toBeVisible();
  await expect(page.getByRole("article").getByText("Not helpful")).toBeVisible();
});

test("dashboard renders documents, search, and RAG citations", async ({ page }) => {
  await page.goto("/dashboard");

  const mockedDashboard = await page.evaluate(async () => {
    const response = await fetch("http://localhost:8000/api/v1/dashboard");
    return response.json();
  });
  expect(mockedDashboard.workspaces).toHaveLength(1);

  await expect(page.getByRole("heading", { name: "Your knowledge base", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Workspace settings" })).toBeVisible();
  await expect(page.getByText("MongoDB Atlas Notes").first()).toBeVisible({ timeout: 15_000 });

  await page.getByPlaceholder("Search notes, documents, summaries, and tags").fill("Atlas");
  await expect(page.getByText("Atlas is a managed MongoDB option.").first()).toBeVisible();

  await page.getByPlaceholder("Ask across notes, uploads, summaries, and indexed chunks").fill("Can I use Atlas?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Use MongoDB Atlas by setting MONGO_URI")).toBeVisible();
  await expect(page.getByRole("link", { name: /MongoDB Atlas Notes Atlas can/ })).toBeVisible();
  await page.getByRole("button", { name: "Helpful", exact: true }).click();
  await expect(page.getByText("Marked helpful")).toBeVisible();
});

test("activity timeline shows audited events", async ({ page }) => {
  await page.goto("/activity");

  await expect(page.getByRole("heading", { name: "Activity timeline" })).toBeVisible();
  await expect(page.getByText("Created note MongoDB Atlas Notes")).toBeVisible();
  await expect(page.getByText("created", { exact: true })).toBeVisible();
  await expect(page.getByText("document", { exact: true })).toBeVisible();
});

test("password reset request and confirm flow works", async ({ page }) => {
  await page.goto("/password-reset");

  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByRole("button", { name: "Create reset token" }).click();
  await expect(page.getByText("reset-token-1234567890")).toBeVisible();

  await page.getByRole("link", { name: "Continue" }).click();
  await page.getByLabel("New password").fill("new-password-123");
  await page.getByRole("button", { name: "Reset password" }).click();
  await expect(page.getByText("Password has been reset.")).toBeVisible();
});
