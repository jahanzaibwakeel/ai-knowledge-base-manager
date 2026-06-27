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

test.beforeEach(async ({ page }) => {
  await page.addInitScript(({ dashboard }) => {
    localStorage.setItem("kbm_token", "test-token");
    const originalFetch = window.fetch.bind(window);
    window.fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const json = (body: unknown) =>
        new Response(JSON.stringify(body), {
          status: 200,
          headers: { "content-type": "application/json" }
        });
      if (url.includes("/api/v1/dashboard/search")) return json({ items: dashboard.recent_documents, limit: 25, offset: 0 });
      if (url.includes("/api/v1/dashboard")) return json(dashboard);
      if (url.endsWith("/api/v1/workspaces")) return json(dashboard.workspaces);
      if (url.includes("/api/v1/workspaces/workspace-1/members")) {
        return json([{ id: "member-1", workspace_id: "workspace-1", user_id: "user-1", email: "owner@example.com", name: "Owner", role: "owner" }]);
      }
      if (url.includes("/api/v1/workspaces/workspace-1/documents")) {
        return json({ items: dashboard.recent_documents, total: 1, limit: 25, offset: 0 });
      }
      if (url.includes("/api/v1/rag/query")) {
        return json({
          answer: "Use MongoDB Atlas by setting MONGO_URI to your cluster connection string.",
          citations: [
            {
              document_id: "doc-1",
              document_title: "MongoDB Atlas Notes",
              chunk_index: 0,
              text: "Atlas can host MongoDB for production knowledge bases."
            }
          ]
        });
      }
      return originalFetch(input, init);
    };
  }, { dashboard });
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
    if (url.endsWith("/workspaces")) {
      return route.fulfill({ headers, json: dashboard.workspaces });
    }
    if (url.includes("/workspaces/workspace-1/members")) {
      return route.fulfill({ headers, json: [{ id: "member-1", workspace_id: "workspace-1", user_id: "user-1", email: "owner@example.com", name: "Owner", role: "owner" }] });
    }
    if (url.includes("/workspaces/workspace-1/documents")) {
      return route.fulfill({ headers, json: { items: dashboard.recent_documents, total: 1, limit: 25, offset: 0 } });
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
    return route.fulfill({ status: 404, headers, json: { detail: "Not mocked" } });
  });
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
});
