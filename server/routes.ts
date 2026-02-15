import type { Express, Request, Response } from "express";
import { createServer, type Server } from "node:http";
import { createProxyMiddleware } from "http-proxy-middleware";

export async function registerRoutes(app: Express): Promise<Server> {
  const apiProxy = createProxyMiddleware({
    target: "http://127.0.0.1:8001",
    changeOrigin: true,
  });

  app.use((req: Request, res: Response, next) => {
    if (req.path.startsWith("/api")) {
      return apiProxy(req, res, next);
    }
    next();
  });

  const httpServer = createServer(app);

  return httpServer;
}
