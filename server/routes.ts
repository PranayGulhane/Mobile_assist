import type { Express } from "express";
import { createServer, type Server } from "node:http";
import { createProxyMiddleware } from "http-proxy-middleware";

export async function registerRoutes(app: Express): Promise<Server> {
  app.use(
    "/api",
    createProxyMiddleware({
      target: "http://127.0.0.1:8001",
      changeOrigin: true,
    }),
  );

  const httpServer = createServer(app);

  return httpServer;
}
